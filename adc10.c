/*****************************************************************************/
/*****************************************************************************/
/*                                                                           */
/*               Honeywell Confidential and Proprietary                      */
/*                                                                           */
/* This work contains valuable confidential and proprietary information.     */
/* Disclosure, use or reproduction outside of Honeywell, Inc. is prohibited  */
/* except as authorized in writing. This unpublished work is protected by    */
/* the laws of the United States and other countries. If publication occurs, */
/* following notice shall apply:                                             */
/*                                                                           */
/*                     Copyright 2003, Honeywell Inc.                        */
/*                         All rights reserved.                              */
/*                Freedom of Information Act(5 USC 522) and                  */
/*         Disclosure of Confidential Information Generaly(18 USC 1905)      */
/*                                                                           */
/* This material is being furnished in confidence by Honeywell, Inc. The     */
/* information disclosed here falls within Exemption (b)(4) of 5 USC 522     */
/* and the prohibitions of 18 USC 1905                                       */
/*                                                                           */
/*****************************************************************************/
/*****************************************************************************/
/*                                                                           */
/* $Archive$ */
/* $Date: 2011-01-31 13:02:32 -0600 (Mon, 31 Jan 2011) $ */
/* $Workfile$ */
/* $Modtime$ */
/* $Author: Tim Nordberg, Radomir Svoboda$ */
/*
 $Log$
*/

// ****************************************************************************
// ****************************************************************************
// FILENAME:           ADC10.C
//
// FILE DESCRIPTION:   Handles almost all access to the on-chip ADC10.
//
// MODULE:             AD Conversion for TI MSP430F22xx
//
// ****************************************************************************
// ****************************************************************************

// ****************************************************************************
// INCLUDE FILES:
//
// Header files of modules referenced by this module are included here.
#include <string.h>
#include <stdint.h>

#include <msp430.h>
#include "global.h"
#include "timer.h"
#include "diag.h"
#include "flash.h"
#include "system.h" // find_sum12b, alternate_sum12b
#include "valve.h"

#include "adc10.h"


#if defined(__MSP430FR2153__) || defined(__MSP430FR2155__) || defined(__MSP430FR2355__)
#define ADC_TEMP_ROOM       30
#define ADC_TEMP_HIGH       105
#define ADC_CAL_GAIN        *((uint16_t *)0x1A16)
#define ADC_CAL_OFFSET      *((uint16_t *)0x1A18)
#define ADC_CAL_15V_ROOM    *((uint16_t *)0x1A1A)
#define ADC_CAL_15V_HIGH    *((uint16_t *)0x1A1C)
#define ADC_CAL_15V_FACTOR  *((uint16_t *)0x1A28)
#define ADC_CAL_20V_FACTOR  *((uint16_t *)0x1A2A)
#define ADC_CAL_25V_FACTOR  *((uint16_t *)0x1A2C)
#else
#error Undefined target for TLV calibration data
#endif

#define ADC_CAL_DIFF            (ADC_CAL_15V_HIGH - ADC_CAL_15V_ROOM)
#define ADC_TEMP_SPAN           (ADC_TEMP_HIGH - ADC_TEMP_ROOM)
#define ADC_TEMP_SCALE_FACTOR   ((ADC_TEMP_SPAN * 9 * 10) / 5)
// ADC_TEMP_ROOM in tenths of degrees Fahrenheit (0.1 °F)
#define ADC_TEMP_ROOM_DECI_DEGF ((ADC_TEMP_ROOM * 18) + 320)

static uint16_t alternate_sum12b(uint16_t channel);
static uint16_t find_sum12b(void);
static uint16_t find_sum14b(void);

static void ConvertAdChannel(uint16_t adcmCtl0);
static void ConvertAdPotAndSensors(void);
static void ClearAdData(void);

// Note: Indexes depend on order in @ref ConvertPotAndSensorsAd function
#define GetPotSum12b() alternate_sum12b(2)
#define GetLtsSum12b() alternate_sum12b(1)
#define GetUtsSum12b() alternate_sum12b(0)

/// TempAmb conversion mutiplier from 12bit AD to 0.1deg F for 1.5 volt AD reference
/**
 * @brief Convert raw 12-bit ADC temperature reading to tenths of a degree Fahrenheit.
 *
 * This function uses two factory-calibrated TLV points (ADC_CAL_15V_ROOM 
 * and ADC_CAL_15V_HIGH) with a 1.5 V reference to perform
 * a two-point linear interpolation.
 *
 * @param adc_temp  Raw 12-bit ADC count from the internal temperature sensor.
 * @return Temperature as an int16_t in units of 0.1 °F.
 */
#pragma optimize=speed
static int16_t TEMP_AMB_14BIT_AD_TO_01DEG_F(int16_t adc_raw_temp)
{
  adc_raw_temp /= DTC_READ_CNT;

  const int32_t deltaTF = ((int32_t)adc_raw_temp - ADC_CAL_15V_ROOM) * ADC_TEMP_SCALE_FACTOR;
  const int16_t degTF = (deltaTF / ADC_CAL_DIFF) + ADC_TEMP_ROOM_DECI_DEGF;
  
  return degTF;
}

/**
 * @brief Corrects raw ADC values read with the 1.5V internal reference.
 * @param raw The raw ADC reading to be corrected
 * @return The corrected ADC value as a uint16_t
 * @note Calculation from TI user guide (SLAU445I 1.13.3.1)
 */
#pragma optimize=speed
static uint16_t ADC_CORRECTED_15REF(uint16_t raw)
{
  int32_t tmp = ((int32_t)raw * ADC_CAL_GAIN) >> 15;
  tmp += ADC_CAL_OFFSET;
  tmp = (tmp * ADC_CAL_15V_FACTOR) >> 15;
  
  return (uint16_t)tmp;
}

/**
 * @brief Corrects raw ADC values read with the 2.0V internal reference.
 * @param raw The raw ADC reading to be corrected
 * @return The corrected ADC value as a uint16_t
 * @note Calculation from TI user guide (SLAU445I 1.13.3.1)
 */
#pragma optimize=speed
static uint16_t ADC_CORRECTED_20REF(uint16_t raw)
{
  int32_t tmp = ((int32_t)raw * ADC_CAL_GAIN) >> 15;
  tmp += ADC_CAL_OFFSET;
  tmp = (tmp * ADC_CAL_20V_FACTOR) >> 15;
  
  return (uint16_t)tmp;
}

/**
 * @brief Corrects raw ADC values read with the 2.5V internal reference.
 * @param raw The raw ADC reading to be corrected
 * @return The corrected ADC value as a uint16_t
 * @note Calculation from TI user guide (SLAU445I 1.13.3.1)
 */
#pragma optimize=speed
static uint16_t ADC_CORRECTED_25REF(uint16_t raw)
{
  int32_t tmp = ((int32_t)raw * ADC_CAL_GAIN) >> 15;
  tmp += ADC_CAL_OFFSET;
  tmp = (tmp * ADC_CAL_25V_FACTOR) >> 15;
  
  return (uint16_t)tmp;
}

#ifdef TESTA
// Methods to expose ADC_CORRECTED_*REF functions for unit testing
uint16_t test_adc_corrected_15ref(uint16_t raw) { return ADC_CORRECTED_15REF(raw); }
uint16_t test_adc_corrected_20ref(uint16_t raw) { return ADC_CORRECTED_20REF(raw); }
uint16_t test_adc_corrected_25ref(uint16_t raw) { return ADC_CORRECTED_25REF(raw); }
#endif

/**
@defgroup gr_adc10 Sensor AD readings and Flame Out detection

  This module performs nearly all AD readings:
  - ambient temperature (@ref TempAmb in @ref task_ad)
  - main valve voltage (@a Vmv12b in @ref task_ad)
  - water temperature (@ref L_Ad1s12b and @ref U_Ad1s12b in @ref task_ad)
  - chamber temperature (@ref C_Ad1_1s12b and @ref C_Ad2_1s12b in @ref task_ad)

  Note that pilot voltage (@ref Vpv12b) is not updated in this module.
  It is supposed to be updated in @ref task_power_management
  and the result is just reused by @ref task_ad to calculate @ref Vtp12b .

@par Usage
  - It is a set of individual procedures and functions.
  - No initialization is required.
  - @ref task_ad should be called at convenient rate, usually once per second.
  - @ref FlameOutDetect should be called at convenient rate, usually once per second.
    DCDC drive should be disabled 10ms before calling this task.
  - to read PV voltage, MV voltage, and Vdd, use
    @ref readVpv, @ref readVmv, and @ref readVdd .
  - to initiate AD conversion, use @ref start_ad .
  - to wait for AD conversion finished, use
    - @ref wait_for_ad_cont (useful in continuous conversion mode because
      it does not stop ADC module), or
    - @ref wait_for_ad (which stops ADC module afterwards and so may save power).
  - to totally switch off and reset the ADC module, use @ref stop_ad .
  - @ref start_and_wait_ad is a combination of @ref start_ad and
    @ref wait_for_ad . It can not be used in continuous mode .
  - @ref dtc_ad configures and performs AD conversion in DTC mode.
    It waits for AD conversion to finish and then stops ADC module.
  - @ref ClearAdData should be called before dtc_ad whenever it is neccessary
    to ensure the buffer for the AD conversion results is empty.

@par Flame Out Detection
  Each time flame out is detected in @ref FlameOutDetect, the timer @ref FlameOutTimer
  is set to @ref INITIAL_FLAMEOUT_TIMER and main valve is shut off.
  The timer is then decremented every second, and unless
  flame out condition is detected again in @ref FlameOutDetect, the timer
  decrements to zero in @ref INITIAL_FLAMEOUT_TIMER seconds (~ 3 minutes).
  Then the main valve is allowed to operate again.

@{
*/

/**
@file adc10.c
@brief Sensor and valve voltage AD readings, flame out detection
@author Tim Nordberg, Radomir Svoboda
@date 2007-06-28
@version 1.0
*/

// ****************************************************************************
// LOCAL DATA:
//
// Memory for local data owned by the module is reserved here. Descriptions of
// the data are contained in the module's header file.  For each data
// item, comments include a description and specify all possible values and
// their meanings.  Any special use of the data item is also specified.

/// @ref POT_MAX_OHMS recalculated to Rpot.
/**
 * RpotOhms = R_BIAS * [ tempUPSS10 * (POT_VDD_AD - tempUPSS01) /
 *   (tempUPSS01 * (POT_VDD_AD - tempUPSS10) - 1],@n
 * but in the software we do not calculate and check potentiometer resistance
 * directly, but rather calculate just the scaled ratio @a Rpot : @n
 * Rpot = POT_MULTIPLIER^2 * [tempUPSS10 * (POT_VDD_AD - tempUPSS01) /
 *   (tempUPSS01 * (POT_VDD_AD - tempUPSS10)] @n
 * where tempUPSS10 is AD reading at NTC1 if UW_SS_CTR = High, LW_SS_STR = Low,@n
 * and tempUPSS01 is AD reading at NTC1 if UW_SS_CTR = HiZ, LW_SS_STR = High,@n
 * see @ref task_ad for details.
 * Rpot is then tested to be between RPOT_MINIMUM and RPOT_MAXIMUM.
 * Since Rpot = RpotOhms / R_BIAS + 1, then RPOT_MAXIMUM is:@n
 * RPOT_MAXIMUM = POT_MAX_OHMS / (R_BIAS / POT_MULTIPLIER^2) + POT_MULTIPLIER^2@n
 * RPOT_MAXIMUM = POT_MULTIPLIER^2 * POT_MAX_OHMS / R_BIAS + POT_MULTIPLIER^2@n
 * The same applies to @ref RPOT_MINIMUM .@n
 * POT_MULTIPLIER is a scale to increase the precission of the calculations.
 */
#define RPOT_MAXIMUM                                                                               \
  (POT_MULTIPLIER * ((1L * POT_MULTIPLIER * POT_MAX_OHMS) / R_BIAS + 1 + POT_MULTIPLIER))

/// @ref POT_MIN_OHMS recalculated to Rpot, see @ref RPOT_MAXIMUM for details.
#define RPOT_MINIMUM                                                                               \
  (POT_MULTIPLIER * ((1L * POT_MULTIPLIER * POT_MIN_OHMS) / R_BIAS + POT_MULTIPLIER))

// ****************************************************************************
// GLOBAL DATA:
//
// Memory for global data owned by the module is reserved here. Descriptions of
// the data are contained in the module's header file.

/// Times out Flame out verification period.
uint8_t FlameOutTimer;

/// History of eight-second averages of thermopile voltage.
static uint16_t VtpHistory13b[FLAME_LOST_QUEUE_SIZE] = { 0, 0, 0, 0, 0, 0, 0, 0 };

/// Actual A/D reading of setpoint potentiometer, 0..4091 (10bit).
uint16_t PotAD;

/// Raw value of Tamb measurement (before calibration companesation)
int16_t TempAmbRaw;

/// storage for AD results in DTC mode of AD conversion
static uint16_t AdData[DTC_CHANNEL_CNT * DTC_READ_CNT];

// ****************************************************************************
// LOCAL FUNCTIONS:
//

static uint16_t VtpDrop(uint16_t vtp);

static void readVpvVmvPart1Setup(void);

//static void readVmv2_5Part1Setup(void);

static inline void readVpvPart2Conversion()
{
  ConvertAdChannel(ADCSREF_1 | ADC12_VPV);
}

static inline void readVmvPart2Conversion()
{
  ConvertAdChannel(ADCSREF_1 | ADC12_VMV);
}

static inline void readVpvVmvPart3PeripheralOff() 
{
  REF_OFF;
}

static uint16_t readVpvVmvPart4GetResult(void);

static uint16_t ConvertAd(void)
{
  ADCCTL0 |= ADCENC | ADCSC; // start conversion
  while (!ADC12_IFG_SET_Q)
    ;             // wait for data
  const uint16_t res = ADCMEM0;
  return res; // return data
}

// ****************************************************************************
// GLOBAL FUNCTIONS:
//

void task_pre_ad(void)
{
  /// @par Safety interlock
  /// First Check @ref safety_interlock and perform software reset if not equal
  /// to @ref PRE_AD_INTERLOCK. then set the interlock to @ref AD_INTERLOCK.
  if (safety_interlock != PRE_AD_INTERLOCK)
  {
    shutdown_system(SDR_TASK_INTERLOCK);
  }
  else
  {
    safety_interlock = AD_INTERLOCK;
  }

  /// Before reading @a Vpv, Pilot Valve drive is turn on (@ref PV_ON)
  /// as well as safety drive regardless of the current mode.
  /// If Pilot Valve pick is not done, the safety drive is not energized.
  /// Turn it on until next task (task_pv) execution by loading
  /// @ref Charge Pump.
  /// Next task in 10ms, MT interrupt is 3.33ms -> 3 shifts (0b00000111)
  if (!PickPV_Done)
  {
    ChargePump = 0x0007; // TODO define properly
  }
}

/**
* @brief This task handles water temperature, ambient temperature, pot position,
* and MV voltage sensing as well as drive fault detection and pot diagnostics.

* All AD readings in this function use the following ADC configuration:
* 64 clock cycle sampling time, use data transfer control (DTC) as data buffer,
* read every channel @ref DTC_READ_CNT (=4) times.
* For each channel the sum of the four samples is calculated and used in
* the following calculations (instead of average to reduce process time).

* Function is called every second. It sets many global variables for use
* in other tasks (@ref g::TempAmb, @ref L_Ad1s12b, @ref U_Ad1s12b,
* @ref PotAD, @ref C_Ad1_1s12b, @ref C_Ad2_1s12b etc.).
* It also performs basics checks on the AD readings
* (e.g. sensors short or open).
*/

void task_ad(void)
{
  int16_t reading;

  typedef enum
  {
    NO_FAULT = 0x00,

    MV_FAULT = 0x01,

    AD_FAULT0    = 0x02,
    AD_FAULT1    = 0x04,
    AD_FAULT2    = 0x08,
    AD_FAULT_ALL = AD_FAULT0 | AD_FAULT1 | AD_FAULT2,

    POT_FAULT0    = 0x10,
    POT_FAULT1    = 0x20,
    POT_FAULT_ALL = POT_FAULT0 | POT_FAULT1,
  } _fault_t;

  _fault_t faults = NO_FAULT;

  /// @par Safety interlock
  /// First Check @ref safety_interlock and perform software reset if not equal
  /// to @ref AD_INTERLOCK. then set the interlock to @ref KNOB_INTERLOCK - 1.
  /// This will be incremented to the correct value of @ref KNOB_INTERLOCK
  /// before returning from this task to ensure that the whole task was executed.
  if (safety_interlock != AD_INTERLOCK)
  {
    shutdown_system(SDR_TASK_INTERLOCK);
  }
  else
  {
    safety_interlock = KNOB_INTERLOCK - 1;
  }

  /// Before reading @a Vpv, Pilot Valve drive is turn on (@ref PV_ON)
  /// regardless of the current mode.
  /// Then @a Vpv is sampled @ref DTC_READ_CNT times and the sum,
  /// shifted by calibration offset (see @ref readVpv), is stored as @ref Vpv12b.
  /// Then if Pilot Valve drive was originally off (i.e. @ref PickPV_Done is false),
  /// it is turned off again.
  /// If safety drive was not energized (if !PickPV_Done) then it was enrgized
  /// in previous task (pre_ad_task).
  // TODO PW Vpv12b used in calibrate?
  // PV and MV ADC reading separated to keep the PV and MV on time as short
  // as possible, similar to Geilee design.
  readVpvVmvPart1Setup();

  // TODO PW fix toogling
  uint8_t block_flag = 0;
  if (BLK_SW_ON_Q())
  {
    block_flag = 1; // Save SF_SW status.
  }
  BLK_SW_ON();
  PV_ON();
  
  readVpvPart2Conversion();

  // Return PV to state before reading.
  if (!PickPV_Done)
  {
    PV_OFF();
  }

  // Part 3: Keep ADC and reference on for next reading

  Vpv12b = ADC_CORRECTED_15REF(readVpvVmvPart4GetResult()); // Baseline Vpv reading.

  if (Fault.Counter.MVDrvShrt == 0 && Fault.Counter.MVDrvOpen != 0 && !MV_ON_Q())
  {
    // mark a flag, so that we don't forget to switch MV off after the ADC is done
    Set(faults, MV_FAULT);
    // if we are suspecting the MV sensing circuit is not working and MV is off
    // then switch it on only for the short time of measuring the Vmv
    MV_ON();
  }

  // Part 1: Same setup, no need to call readVpvVmvPart1Setup() again

  readVmvPart2Conversion();

  if (Test(faults, MV_FAULT))
  {
    // we see the mark, switch MV off - end of the MV reading circuit test
    MV_OFF();
  }

  if (block_flag == 0)
  {
    BLK_SW_OFF();
  }

  readVpvVmvPart3PeripheralOff();

  uint16_t Vmv12b = ADC_CORRECTED_15REF(readVpvVmvPart4GetResult());

  /// Test for MV driver or ADC faults:
  /// # MV on (MV_CTR = high), and @n
  ///   no MV voltage is sensed, i.e. Vmv12b < @ref VMV_TEST_THRESH @n
  ///   => increment @ref T_FAULT_COUNTER::MVDrvOpen fault counter (@ref Fault)
  ///     by @ref MV_DRV_OPEN_FAULT_INC, @n
  ///   otherwise decrement the fault counter by one.
  /// # MV is on (MV_CTR = high), and @n
  ///   MVDrvOpen not mature, and @n
  ///   MV and PV voltages do not match, i.e.
  ///     ABS(Vmv12b - @ref Vpv12b) > @ref VPV_VMV_MAX_DIFF, @n
  ///   => increment @ref T_FAULT_COUNTER::AD fault counter (@ref Fault)
  ///     by @ref AD_FAULT_INC, @n
  ///   otherwise decrement the fault counter by one,
  ///   but only if also the other (following) checks of ADC pass.
  /// # MV is off (MV_CTR = low), and @n
  ///   MV voltage is present (Vmv12b < @ref VMV_TEST_THRESH), @n
  ///   => increment @ref T_FAULT_COUNTER::MVDrvShrt fault counter (@ref Fault)
  ///     by @ref MV_DRV_SHRT_FAULT_INC), @n
  ///   otherwise decrement the fault counter by one.
  if (MV_ON_Q() || Test(faults, MV_FAULT))
  {
    // MV is on or we are "sampling" the MV reading circuit during MV off
    // convert VMV_TEST_THRESH from milivolts to AD counts
    // (sum of DTC_OUTPUT_CNT samples, 1.5V reference)
    // PW note: On Geilee, MVDrvOpen was checked before picking MV
    // + it prevents it to pick MV.
    // MVDrvOpen is now tested after MV pick, but it should not
    // caused any issue/safety issue.
    const uint16_t open_thresh = AD_VMV(VMV_TEST_THRESH_OPEN);
    if (Vmv12b < open_thresh)
    {
      // only debounce MV_DRV_OPEN if PV_SF_SW is not open
      if (Fault.Counter.PV_SF_DrvOpen == 0)
      {
        // MVDriver is open
        Fault.Counter.MVDrvOpen += MV_DRV_OPEN_FAULT_INC;
      }
    }
    else
    {
      deb_down(&Fault.Counter.MVDrvOpen, MV_DRV_OPEN_FAULT_DEC);

      if (MV_ON_Q())
      {
        // check Vmv compared to Vpv, must be close or AD is failed
        uint16_t diff = Vmv12b > Vpv12b ? (Vmv12b - Vpv12b) : (Vpv12b - Vmv12b);
        // convert VPV_VMV_MAX_DIFF from milivolts to AD counts
        // (sum of DTC_OUTPUT_CNT samples, 1.5V reference)
        if (diff > AD_VPV(VPV_VMV_MAX_DIFF))
        {
          Set(faults, AD_FAULT0);
        }
      }
    }
  }
  else
  {
    // MV is off
    // convert VMV_TEST_THRESH from milivolts to AD counts
    // (sum of DTC_OUTPUT_CNT samples, 1.5V reference)
    const uint16_t thresh = AD_VMV(VMV_TEST_THRESH_SHORT);
    if (Vmv12b >= thresh)
    {
      Fault.Counter.MVDrvShrt += MV_DRV_SHRT_FAULT_INC; // MVDriver is shorted
    }
    else if (Fault.Counter.MVDrvShrt)
    {
      Fault.Counter.MVDrvShrt--;
    }
  }

  // TODO PW verify settling time and sample times

  /// @par AD reading #1 - internal temperature sensor
  /// - Use internal AD reference 1.5V
  /// - Set up A/D to read the internal temperature sensor voltage
  /// - Store the sum of the AD reading as tempOnChipSS12b
  /// - During the next AD conversion (MV voltage), calculate
  ///   the ambient temperature and store it as @ref T_SERIAL_DATA::TempAmb : @n
  ///   @a TempAmb = TEMP_AMB_12BIT_AD_TO_DEG_F_MULTI(tempOnChipSS12b)
  ///     - @ref T_CALI_DATA::OnChipSSOffset ,
  ///   where @a OnChipSSOffset is the typical temperature offset obtained
  ///   during calibration
  /// - Limit @a TempAmb between @ref TEMP_AMB_MIN and @ref TEMP_AMB_MAX (�F).

  TS_OFF();    // UW_SS_CTR and LW_SS_CTR output low
  TS_OUTPUT(); // needed only after startup, which uses LW_SS_CTR as input
  // to sense RS232 adapter,
  // but then not needed, because REINIT_PORT_3 is done every second
  // in the diagnostics task

  // ADC10CTL0 = SREF_1 | ADC10SHT_3 | MSC | ADC10ON | REFON;
  // dtc_ad(ADC10_TS);

  REF_1_5V_TS_ON;
  // sample time > 30us, MODOSC max 4.8MHz -> 138 min ADC cycles
  ADCCTL0 = ADCSHT_7 | ADCMSC | ADCON;
  ADCCTL1 = ADCSHS_0 | ADCSHP | ADCDIV_0 | ADCSSEL_0;
  ADCCTL2 = ADCPDIV_0 | ADCRES_2;

  ConvertAdChannel(ADCSREF_1 | ADC12_TS); // do conversion
  REF_OFF; // turn AD internal reference off, Vcc used for sensor/pot/chamber

  // store previous result
  uint16_t tempOnChipSS14b = find_sum14b(); // sum of obtained AD results

  // process the ambient temperature
  TempAmbRaw           = TEMP_AMB_14BIT_AD_TO_01DEG_F(tempOnChipSS14b);
  int16_t localTempAmb = TempAmbRaw - CaliDataPtr->OnChipSSOffset;

  if (localTempAmb > TEMP_AMB_MAX)
  {
    localTempAmb = TEMP_AMB_MAX;
  }
  else if (localTempAmb < TEMP_AMB_MIN)
  {
    localTempAmb = TEMP_AMB_MIN;
  }
  else
  {
#ifdef LOW_TEMP_AMB
    localTempAmb = TEMP_AMB_MIN;
#endif
  }
  TempAmb = localTempAmb; // TempAmb is in 0.1deg F

  /// @par Normal Pilot Valve voltage VpvNorm12b
  /// Update @ref VpvNorm12b, because valve coil resistance depends on
  /// temperature:@n
  /// VpvNorm = @ref VPV_NORM_OFFSET + 0.03666 * @ref g.TempAmb @n
  /// The constant 0.03666 was found experimentally and if VpvNorm12b and
  /// VPV_NORM_OFFSET are 12bit AD results than the constant
  /// converts to 1/10 :@n
  /// @ref VpvNorm12b = VPV_NORM_OFFSET_12b + @ref g.TempAmb @n
  /// If new VpvNorm12b is higher than previous VpvNorm12b,
  /// then adjust @ref VpvNorm12b value by one count up.
  /// If VpvNorm12bNew is smaller than VpvNorm12b,
  /// then decrement @ref VpvNorm12b by one.

  // calculate new desired VpvNorm12b value
  reading = AD_VPV(VPV_NORM_OFFSET) + TempAmb / DEGF_TO_TEMPCTRL_UNITS(1);
  // only adjust VpvNorm12b one step at a time if different from current
  if (reading > VpvNorm12b)
  {
    VpvNorm12b++;
  }
  else if (reading < VpvNorm12b)
  {
    VpvNorm12b--;
  }

  /// @par AD reading #2 - Water sensor & pot - Low-Low
  /// - Set up water sensor interface:
  ///   - UW_SS_CTR = Low
  ///   - LW_SS_CTR = Low
  /// - Set up A/D to convert in sequence of channels mode to read each
  ///   of the first 8 ADC channels @ref DTC_READ_CNT times
  ///   @ref DTC_CHANNEL_CNT * DTC_READ_CNT readings in total.
  /// - Use Vdd (Vcc) as reference.
  /// - Before starting the AD conversion, clear the AdData buffer.
  /// - To save time, set up and start A/D reading already before processing
  ///   the AD value of the MV voltage, as described in the previous paragraph
  /// - Store the sums of the AD readings as tempPot00, tempLWSS00, and
  ///   tempUPSS00

  // Setup AD for Pot/Sensor readings, uses repeated sequence of
  // channels mode, 4 conversions each
  // AD ref = Vcc, sample&hold time = 64clks,
  //  ADC10CTL0 = SREF_0 | ADC10SHT_3 | MSC | ADC10ON;
  //  ADC10CTL1 = ADC10_UTS | CONSEQ_3;
  //  ADC10DTC1 = DTC_CHANNEL_CNT * DTC_READ_CNT;
  //  ClearAdData(); // clear AdData buffer
  //  start_ad();
  ADCCTL0 = ADCSHT_4 | ADCMSC | ADCON;
  ADCCTL1 = ADCSHS_0 | ADCSHP | ADCDIV_0 | ADCSSEL_0;
  ADCCTL2 = ADCPDIV_0 | ADCRES_2;

  ClearAdData(); // clear AdData buffer
  ConvertAdPotAndSensors();

  UTS_ON(); // Setup bias to get ready for the second set (UP=1, LW=0).

  // store results of the first set (UP=0, LW=0)
  uint16_t tempPot00  = GetPotSum12b();
  uint16_t tempLWSS00 = GetLtsSum12b();
  uint16_t tempUPSS00 = GetUtsSum12b();

  /// Check that all three results are close to zero (ground, logical low): @n
  /// tempPot00, tempLWSS00, tempUPSS00 <= @ref GND_TEST_THRESH_AD @n
  /// If any of them is higher,
  /// increment @ref T_FAULT_COUNTER::AD (@ref Fault) fault counter
  /// by @ref AD_FAULT_INC. @n
  /// Otherwise decrement the fault counter by one,
  /// but only if also all the other AD checks pass.

  // correct GND_TEST_THRESH_AD to the scale of DTC_OUTPUT_CNT readings
  if ((tempPot00 > (GND_TEST_THRESH_AD * DTC_OUTPUT_CNT)) ||
      (tempLWSS00 > (GND_TEST_THRESH_AD * DTC_OUTPUT_CNT)) ||
      (tempUPSS00 > (GND_TEST_THRESH_AD * DTC_OUTPUT_CNT)))
  {
    Set(faults, AD_FAULT1);
  }

  /// @par AD reading #3 - Water sensor & pot - High-Low
  /// - Set up water sensor interface:
  ///   - UW_SS_CTR = High
  ///   - LW_SS_CTR = Low
  /// - use A/D settings from the previous paragraph
  /// - Before starting the AD conversion, clear the AdData buffer
  /// - To save time, set up and start A/D reading already before processing
  ///   the AD value of the LL readings, as described in the previous paragraph
  /// - Store the sums of the AD readings as tempPot10, tempLWSS10,
  ///   and tempUPSS10.

  // start second set of Pot/Sensor conversions (UP=1, LW=0).
  ClearAdData();
  ConvertAdPotAndSensors();

  LTS_ON(); // Setup bias for third set of conversions (UP=1, LW=1).

  // store results of the second set (UP=1, LW=0)
  uint16_t tempPot10  = GetPotSum12b();
  uint16_t tempUPSS10 = GetUtsSum12b();

  /// Store @a tempPot10 to the global @ref PotAD
  /// (will be used as the actual pot reading).
  PotAD = tempPot10;

  /// @par AD reading #4 - Water sensor & pot - High-High
  /// - Set up water sensor interface:
  ///   - UW_SS_CTR = High
  ///   - LW_SS_CTR = High
  /// - use A/D settings from the previous paragraph
  /// - Before starting the AD conversion, clear the AdData buffer
  /// - To save time, set up and start A/D reading already before processing
  ///   the AD value of the HL reading, as described in the previous paragraph
  /// - Store the sum of the AD readings as tempPotFS, @ref L_Ad1s12b, and
  ///   @ref U_Ad1s12b .
  /// - When conversion is done, set the UW_SS_CTR and LW_SS_CTR pins as HiZ inputs.

  // start third set of Pot/Sensor conversions (UP=1, LW=1)
  ClearAdData();
  ConvertAdPotAndSensors();

  // Setup bias for next set of conversions (UP=HiZ, LW=1).
  UTS_INPUT();
  UTS_OFF();

  // store results of the third set (UP=1, LW=1)
  uint16_t tempPot11  = GetPotSum12b();
  uint16_t tempLWSS11 = GetLtsSum12b();
  uint16_t tempUPSS11 = GetUtsSum12b();

  /// <b>Upper and Lower sensor short/open test</b>@n
  /// Applied on ecah of the two NTC sensors individually.
  /// Each sensor has its own open/short fault counter.@n
  /// Fault condition: AD_reading > SS_OPEN_AD (open sensor)
  /// or AD_eading < SS_SHORT_AD (sensor shorted).
  /// On fault, fault counter is debounced up at a rate of
  /// SENSOR_FAULT_INC counts per second.
  /// If sensor passes the test, fault counter is decremented
  /// using @ref generic_deb_down function.

  /// <b>Upper-Lower short test</b>@n
  /// Ideally, Upper_AD_reading (NTC2) should be zero.@n
  /// Fault condition: Upper_AD_reading > 1/3 * SS_SHORT_AD (sensor short threshold)

  // upper sensor open/short test
  reading = (tempUPSS10 > tempUPSS11) ? (tempUPSS10 - tempUPSS11) : (tempUPSS11 - tempUPSS10);
  // lower sensor open/short test, sensors shorted test
  if ((tempLWSS11 > (SS_OPEN_AD * DTC_OUTPUT_CNT)) ||
      (tempLWSS11 < (SS_SHORT_AD * DTC_OUTPUT_CNT)) || (reading > (SS_LH_DIFF_AD * DTC_OUTPUT_CNT)))
  {
    Fault.Counter.LSOpenShrt += SENSOR_FAULT_INC;
    Set(faults, POT_FAULT0); // sensors are not o.k. -> disable pot test
  }
  else
  {
    L_Ad1s12b = tempLWSS11;
    generic_deb_down(&Fault.Counter.LSOpenShrt);
  }

  if ((tempUPSS11 > (SS_OPEN_AD * DTC_OUTPUT_CNT)) ||
      (tempUPSS11 < (SS_SHORT_AD * DTC_OUTPUT_CNT)) || (reading > (SS_LH_DIFF_AD * DTC_OUTPUT_CNT)))
  {
    Fault.Counter.USOpenShrt += SENSOR_FAULT_INC;
    Set(faults, POT_FAULT0); // sensors are not o.k. -> disable pot test
  }
  else
  {
    U_Ad1s12b = tempUPSS11;
    generic_deb_down(&Fault.Counter.USOpenShrt);
  }

  /// <b>AD full scale test</b>@n
  /// When Both NTCs are biased to Vdd, pot reading should be close to
  /// maximuml AD.@n
  /// Fault condition: tempPot11 < @ref MINIMUM_WIPER_AD_CHK, @n
  /// On fault, increment AD fault by @ref AD_FAULT_INC).@n
  if (tempPot11 < (MINIMUM_WIPER_AD_CHK * DTC_OUTPUT_CNT))
  {
    Set(faults, AD_FAULT2);
  }

  // finish debouncing ad_fault -- used to make sure we do not
  // have interaction in each second between fault detection
  // (i.e. incrementing twice or incrementing and decrementing etc...)
  if (Test(faults, AD_FAULT_ALL))
  {
    PotAD = POT_INVALID;
    Fault.Counter.AD += AD_FAULT_INC;
  }
  else
  {
    generic_deb_down(&Fault.Counter.AD);
  }

  /// @par AD reading #5 - Water sensor & pot - HiZ-High
  /// - Set up water sensor interface:
  ///   - UW_SS_CTR = HiZ
  ///   - LW_SS_CTR = High
  /// - use A/D settings from the previous paragraph
  /// - Before starting the AD conversion, clear the AdData buffer
  /// - To save time, set up and start A/D reading already before processing
  ///   the AD value of the HH reading, as described in the previous paragraph
  /// - Store the sums of the AD readings as tempPot01 and
  ///   tempUPSS01
  // start forth set of Pot/Sensor conversions (UP=HiZ, LW=1)
  ClearAdData();
  ConvertAdPotAndSensors();

#ifdef DOOR_SENSOR
  // setup for chamber temperature reading (CH_IN=HiZ, CH_CTR=1)
  CTS_INPUT;
#endif
  // turn temp sensors off
  TS_OFF();
  TS_OUTPUT();

  // store results of the forth set (UP=HiZ, LW=1)
  uint16_t tempPot01  = GetPotSum12b();
  uint16_t tempUPSS01 = GetUtsSum12b();

  /// Check setpoint potentiometer. @n
  /// However, check the pot only if the NTC sensors are o.k., otherwise
  /// pot fault could be falsely indicated for sensor failures.
  /// Fault conditions:
  /// - Pot reading is higher than the upper sensor reading for
  ///   UW_SS_CTR=HiZ nad LW_SS_CTR=High: @n
  ///   tempPot01 < tempUPSS01 + @ref POT_REQD_INCREASE_AD
  /// - estimated full resistance of the pot is out of range: @n
  ///   @ref RPOT_MINIMUM < @a Rpot < @ref RPOT_MAXIMUM, @n
  ///   where @a Rpot = (tempUPSS10 * (@ref POT_VDD_AD - tempUPSS01)) /
  ///         (tempUPSS01 * (@ref POT_VDD_AD - tempUPSS10))
  if (!Test(faults, POT_FAULT_ALL))
  {
    // Pot reading should be higher than upper sensor reading
    if (tempPot01 < (tempUPSS01 + (POT_REQD_INCREASE_AD * DTC_OUTPUT_CNT)))
    {
      Set(faults, POT_FAULT0);
    }
    else
    {
      // calculate Rpot
      // POT_MULTIPLIER allows for better resolution in 16bit
      uint16_t Rpot = (POT_MULTIPLIER * tempUPSS10) / tempUPSS01;
      Rpot *= (POT_MULTIPLIER * (POT_VDD_AD * DTC_OUTPUT_CNT - tempUPSS01)) /
              (POT_VDD_AD * DTC_OUTPUT_CNT - tempUPSS10);

      if ((Rpot > RPOT_MAXIMUM) || (Rpot < RPOT_MINIMUM))
      {
        Set(faults, POT_FAULT1);
      }
    }

    /// If any of the fault conditions is true, Pot fault counter
    /// is debounced up by POT_FAULT_INC.@n
    /// If both tests passed successfully, Pot fault is debounced down,
    /// using @ref generic_deb_down .
    if (Test(faults, POT_FAULT_ALL))
    {
      Fault.Counter.Pot += POT_FAULT_INC;
      PotAD = POT_INVALID;
    }
    else
    {
      generic_deb_down(&Fault.Counter.Pot);
    }
  }

#ifdef DOOR_SENSOR
  /// @par AD reading #6 - Chamber sensor - High-HiZ (2.1K pullup)
  /// - set up chamber sensor interface to use 2.1k pullup
  /// - Use Vdd (Vcc) as reference.
  /// - Before starting the AD conversion, clear the AdData buffer
  /// - To save time, set up and start A/D reading already before processing
  ///   the AD value of the water sensor xH reading from the previous paragraph
  /// - Store the sum of the AD readings as @ref C_Ad1_1s12b
  // start chamber temperature measurement
  // AD channel: Chamber Temp Sensor, mode: repeated single
  // ADC10CTL1 = ADC10_CTS | CONSEQ_2;
  // ADC10DTC1 = DTC_READ_CNT;
  ADCCTL0 = ADCSHT_4 | ADCMSC | ADCON;
  ADCCTL1 = ADCSHS_0 | ADCSHP | ADCDIV_0 | ADCSSEL_0;
  ADCCTL2 = ADCPDIV_0 | ADCRES_2;

  ClearAdData(); // clear AdData buffer
  ConvertAdChannel(ADCSREF_0 | ADC12_CTS);

  // setup for chamber sensor test (CH_IN=1, CH_CTR=HiZ)
  CTS_TEST;

  // store chamber temperature reading
  C_Ad1_1s12b = find_sum12b();

  /// @par AD reading #7 - Chamber sensor - HiZ-High (10K pullup)
  /// - set up chamber sensor interface to use 10k pullup
  /// - Use A/D setting from the previous paragraph
  /// - Before starting the AD conversion, clear the AdData buffer
  /// - Store the sum of the AD readings as @ref C_Ad2_1s12b
  /// - Switch off the chamber sensor interface
  ClearAdData();
  ConvertAdChannel(ADCSREF_0 | ADC12_CTS);

  // chamber sensor conversion done - turn off ADC
  ADC12_OFF;
  // turn chamber interface off
  CTS_OFF;

  C_Ad2_1s12b = find_sum12b();
#endif

  // increment interlock to = KNOB_INTERLOCK
  safety_interlock++;
}



// Order must match training exactly:
// [1, TP, TP^2, MV, MV*TP, BO*baseline_filled, BO]
typedef struct {
    float w0;  // intercept
    float w1;  // TP
    float w2;  // TP^2
    float w3;  // MV
    float w4;  // MV*TP
    float w5;  // BO*baseline_filled
    float w6;  // BO
} CalibCoefs;


// Fill these from your Python fit results (same numeric scale as features)
static const CalibCoefs gC = {
    .w0 =  6.40844518e+02f,
    .w1 = -7.82691231e-01f,
    .w2 =  6.81640001e-04f,
    .w3 = -1.21841382e+01f,
    .w4 =  9.60909375e-02f,
    .w5 =  5.48220737e-01f,
    .w6 = -4.13771474e+02f,
};


typedef struct {
    float alpha;          // 0<alpha<=1 (e.g., 0.1)
    bool  skip_first_after_fall;

    // runtime state
    float ema;
    uint8_t have_ema;
    uint8_t prev_bo;
    uint8_t cooldown;     // 1 to skip first 0 after fall
} BaselineEMA;


static BaselineEMA ema_state;


static inline uint16_t sat_u16_from_float(float v) {
    if (v < 0.0f) v = 0.0f;
    if (v > 65535.0f) v = 65535.0f;
    return (uint16_t)(v + 0.5f); // round to nearest
}


static inline void BaselineEMA_Init(BaselineEMA *st, float alpha, bool skip_first_after_fall) {
    st->alpha = alpha;
    st->skip_first_after_fall = skip_first_after_fall;
    st->ema = 0.0f;
    st->have_ema = 0;
    st->prev_bo = 0;
    st->cooldown = 0;
}


/**
 * Update baseline EMA with uint16_t samples; returns uint16_t baseline and valid flag.
 * - While bo==0: update EMA unless skipping the first sample after a 1->0 fall.
 * - While bo==1: freeze EMA; output baseline (valid=1) if EMA exists, else valid=0.
 *
 * Inputs:
 *   tp  : current ADC sample (uint16_t, same units as training unless scaled later)
 *   bo  : clamp flag (0/1)
 * Outputs:
 *   *baseline_out       : uint16_t baseline (only meaningful if baseline_valid_out==1)
 *   *baseline_valid_out : 0/1
 */
static inline void BaselineEMA_Update(BaselineEMA *st, uint16_t tp, uint8_t bo,
                                      uint16_t *baseline_out, uint8_t *baseline_valid_out)
{
    // Detect falling edge: 1 -> 0
    if (st->skip_first_after_fall && st->prev_bo == 1 && bo == 0) {
        st->cooldown = 1;
    }

    if (bo == 0) {
        // Update EMA unless skipping after a fall
        if (st->cooldown > 0) {
            st->cooldown--;
        } else {
            float tp_f = (float)tp;
            if (!st->have_ema) {
                st->ema = tp_f;      // seed
                st->have_ema = 1;
            } else {
                st->ema = st->alpha * tp_f + (1.0f - st->alpha) * st->ema;
            }
        }
        *baseline_valid_out = 0;
        *baseline_out = 0u;          // undefined when invalid
    } else {
        if (st->have_ema) {
            *baseline_out = sat_u16_from_float(st->ema);
            *baseline_valid_out = 1;
        } else {
            *baseline_out = 0u;
            *baseline_valid_out = 0;
        }
    }
}



// Call once at startup
void calib_init(void) {
    // alpha must match your intended smoothing; 0.1f is a good default
    // alpha=1, skip is true
    BaselineEMA_Init(&ema_state, 0.5, true);
}


uint16_t vtp_open(void) {
  uint16_t tp = Vpv12b;
  uint8_t bo = SYNC_BOOST_ON_Q;
  uint8_t mv = MV_ON_Q();

  uint16_t base; 
  uint8_t base_valid; 
  // Call either MA or EMA updater
  BaselineEMA_Update(&ema_state, tp, bo, &base, &base_valid);

  // Build features safely
  uint16_t baseline_filled = (base_valid ? base : tp);

  // --- Features per A order ---
  const float TP2     = tp * tp;                // compute in float to avoid integer overflow
  const float MV_TP   = mv * tp;
  const float BO_BASE = ((float)bo) * baseline_filled;


    // y = w0 + w1*TP + w2*TP^2 + w3*MV + w4*(MV*TP) + w5*(BO*baseline_filled) + w6*BO
    float y_f = gC.w0
      + gC.w1 * tp
      + gC.w2 * TP2
      + gC.w3 * mv
      + gC.w4 * MV_TP
      + gC.w5 * BO_BASE
      + gC.w6 * (float)bo;

    // Convert to desired output units; here we return a 16-bit value
    return sat_u16_from_float(y_f);
    //return y_f;
}


/**
 * @brief Function called every second to sense thermopile voltage
 * and track possible flame lost.
 */
  /// Ensure that before calling this function the DCDC has been turned off
  /// for one main loop period (10 ms) to allow easier calculation
  /// of open circuit thermopile voltage (all power from thermopile goes to
  /// valves only).

  /// FlameOut Detection should be disabled upon initial reset
  /// until the pilot valve has been picked.
  /// This ensures flameout is not detected on shutdown / reset
  /// before power is fully decayed.

  /// @par Thermopile voltage reading
  /// We store the normalized valve voltage as @ref Vtp12b (12 bit AD),
  /// which is the valve voltage as it would be if both valves
  /// were open (energized) at the same time (= full load) .@n
  /// We use PV voltage @ref Vpv12b, which is measured with enabled power
  /// source for MCU. This error must be corrected.
  /// On Vesta, @ref Vpv12b was measured while DCDC was off.
  /// Therefore if MV was on (MV_ON_Q) @ref Vpv12b reading was also
  /// the wanted @ref Vtp12b.
  /// Input data for Vesta calculation for reference:
  /// Typical valve coil resistances @a Rmv = @ Rpv = 11 Ohms,
  /// and typical thermopile resistance @a Rtp = 3 Ohms.@n
void FlameOutDetect(void)
{
  static uint8_t sumCounter = 0;


  int32_t vtpReading12b = Vpv12b;


  /// Probably experimantally determined correction characteristic.
  if (!MV_ON_Q())
  {
    if (!PickPV_Done)
    {
      vtpReading12b += (((25 * vtpReading12b) + 50) / 100) - 124;
      vtpReading12b *= NO_LOAD_TO_PVMV_LOAD_MULT;
    }
    else
    {
      vtpReading12b += (((25 * vtpReading12b) + 50) / 100) - 100;
      vtpReading12b *= PV_LOAD_TO_PVMV_LOAD_MULT;
    }
    vtpReading12b /= XX_LOAD_TO_PVMV_LOAD_DIV;
  }
  else
  {
    if (vtpReading12b < 880)
    {
      vtpReading12b += (((20 * vtpReading12b) + 50) / 100) - 45;
    }
    else
    {
      vtpReading12b += (((27 * vtpReading12b) + 50) / 100) - 90;
    }
  }
  Vtp12b = vtpReading12b > 0 ? (uint16_t) vtpReading12b : 0;
//  if (!MV_ON_Q())^M

  // FIXME: hack for motor cap boost, based on quick empirical observation
  if (SYNC_BOOST_ON_Q)
  {
    Vtp12b += 40;
  }


  /// @par Flameout detection
  /// The software sums FLAME_LOST_SUM_AMOUNT (=8) subsequent values of @ref Vtp12b
  /// to achieve an 8-second average (sum of 32 readings).
  /// Each 8-second average is shifted into a FIFO queue (@ref VtpHistory13b).
  /// The size of the queue is @ref FLAME_LOST_QUEUE_SIZE (=8) samples.
  /// This creates a record of the last 64 (8*8) seconds of thermopile voltage.

  // reduce Vtp12b to 10 bits first, so the resulting sum will be 13 bits
  VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 1] += (Vtp12b >> 2);

  if (++sumCounter >= FLAME_LOST_SUM_AMOUNT)
  {

    // clear sumCounter to start another set of FLAME_LOST_SUM_AMOUNT samples
    sumCounter = 0;

    if (VtpHistory13b[0] == 0)
    {
      /// After start-up, when the first 8-second sum is ready,
      /// the whole @ref VtpHistory13b queue is initialized to
      /// that first sum, creating an virtual image of a steady flame.
      for (uint16_t i = 0; i < FLAME_LOST_QUEUE_SIZE - 1; i++)
      {
        VtpHistory13b[i] = VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 1];
      }
    }

    /// @a vtpNormal is updated every eight seconds as the sum of four oldest
    /// records.
    /// Thus, @a vtpNormal corresponds to average flame strength between 32s to 64s ago.
    // oldest readings are at the beginning of the queue (slots 0, 1 ...)
    uint16_t vtpNormal15b = 0;
    for (uint16_t i = 0; i < (FLAME_LOST_QUEUE_SIZE / 2); i++)
    {
      vtpNormal15b += VtpHistory13b[i];
    }

    /// Flame out is detected and @ref FlameOutTimer is started (initialized
    /// to @ref INITIAL_FLAMEOUT_TIMER = 180 seconds):
    /// - if the latest record in @a vtpHistory (~ average flame strength during last 8 seconds)
    ///   dropped under 50% of @a vtpNormal (~ average flame strength between 32 to 64 seconds ago),
    /// - if the latest record in @a vtpHistory dropped under 80% of @a vtpNormal,
    ///   and the latest three records (~ last 24 seconds) indicate that
    ///   the flame strength drops continuously by more than 12.5% per 8 seconds
    ///   (6.25% in Off mode).
    ///
    /// When @ref FlameOutTimer is not zero, the timer is decremented
    /// in the main valve task @ref task_mv and it forces the main valve
    /// to turn off while the timer is active (non-zero).
    /// This will allow the system to remain in operation if the pilot flame
    /// lost condition was detected incorrectly.

    // vtpNormal15b (15 bits) to 13 bits -> (vtpNormal15b >> 2)
    // 50% of (vtpNormal15b >> 2) -> (vtpNormal15b >> 3)
    if ((VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 1] < (vtpNormal15b >> 3))
        // 80% of (vtpNormal15b >> 2) = (vtpNormal15b / 4) * 8 / 10 = (vtpNormal15b * 2) / 10 ...
        || ((VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 1] < (vtpNormal15b * 2) / 10)
            // ... and Vtp has been decreasing continously over last three records
            // by 12.5% (6.25% in off mode) or faster
            && (VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 2] <
                (VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 3] -
                 VtpDrop(VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 3] >> 3))) &&
            (VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 1] <
             (VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 2] -
              VtpDrop(VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 2] >> 3)))))
    {
      // all drops higher than 12.5% (6.25% in Off mode) -> flame out proved
      FlameOutTimer = INITIAL_FLAMEOUT_TIMER;
    }

    // shift data to free the first slot
    for (uint16_t i = 1; i < FLAME_LOST_QUEUE_SIZE; i++)
    {
      VtpHistory13b[i - 1] = VtpHistory13b[i];
    }
    VtpHistory13b[FLAME_LOST_QUEUE_SIZE - 1] = 0;
  }
}

/**
* @brief Reads Vdd (digital source voltage)
* @param ref AD reference voltage: REF_1_5 (internal 1.5 VDC) or
*   REF_2_5 (internal 2.5 VDC)
* @return the obtained AD value, 10 bit resolution (0..1023)

* Function is called at various points in execution to read
* the current value of Vdd. Only one AD conversion is performed.
*/
uint16_t readVdd(void)
{
  /// AD configuration:
  /// - ADC10CTL1: channel Vdd, single conversion, ADC clock = ACLK
  /// - ADC10CTL0: internal reference (1.5v or 2.5v), adc on,
  ///   reference generator on, sample and hold time 64 x ADC clock ( = 64us)
  // ADC10CTL1 = ADC10_VDD | CONSEQ_0;
  // if(ref == REF_1_5)
  //{
  //   // reference 1.5v
  //   ADC10CTL0 = SREF_1 | ADC10ON | REFON | ADC10SHT_3;
  // }
  // else
  //{
  //   // reference 2.5v
  //   ADC10CTL0 = SREF_1 | ADC10ON | REFON | ADC10SHT_3 | REF2_5V;
  // }

  REF_1_5V_ON;
  ADCCTL0  = ADCSHT_4 | ADCON;
  ADCCTL1  = ADCSHS_0 | ADCSHP | ADCDIV_0 | ADCSSEL_0;
  ADCCTL2  = ADCPDIV_0 | ADCRES_2;
  ADCMCTL0 = ADCSREF_0 | ADC12_REF;

  while (!REF_GENRDY)
    ;                        // wait for internal reference (TODO 100us)
  ADCCTL0 |= ADCENC | ADCSC; // start conversion
  while (!ADC12_IFG_SET_Q)
    ; // wait for data

  REF_OFF;                   // reference off
  const uint16_t result = ADC_CORRECTED_15REF(ADCMEM0);
  ADC12_STOP;                // stop ADC
  // invert result to get logical comparison
  // otherwise the value is gets smaller when Vcc increases
  return 0x0FFF - result;
}

static void readVpvVmvPart1Setup(void)
{
  REF_1_5V_ON;
  ADCCTL0 = ADCSHT_4 | ADCMSC | ADCON;
  ADCCTL1 = ADCSHS_0 | ADCSHP | ADCDIV_0 | ADCSSEL_0;
  ADCCTL2 = ADCPDIV_0 | ADCRES_2;
}

static uint16_t readVpvVmvPart4GetResult(void)
{
  // sum the 4 AD readings
  int16_t read_sum = find_sum12b();
  // add calibrated offset
  read_sum += CaliDataPtr->VinOffset12b; // adjust with vin calibration offset
  // fix for possible negative offset...
  if (read_sum < 0)
  {
    read_sum = 0;
  }
  return (uint16_t) read_sum;
}

/**
* @brief Reads Pilot valve voltage
* @return the obtained AD value, 12 bit resolution (0..4092)

* Function called at various points in execution to read
* VIN. It reads the Vtp AD channel @ref DTC_READ_CNT (4) times,
* sums the four AD results to obtain a 12 bit value,
* and adds calibrated vin offset (@ref T_CALI_DATA::VinOffset12b, @ref Info)
* to the result.
*/
uint16_t readVpv(void)
{
  /// AD configuration:
  /// - ADC10CTL0: internal reference 1.5v,
  ///   sample and hold time 16 x ADC clock,
  ///   multiple sample and conversion on,
  ///   ADC on,
  ///   reference generator on,
  /// - ADC10CTL1: AD channel = Vpv, repeat-single-channel mode
  /// - ADC10DTC1: number of conversions = @ref DTC_READ_CNT
  // ADC10CTL0 = SREF_1 | ADC10SHT_2 | MSC | ADC10ON | REFON;
  // dtc_ad(ADC10_VPV);
  // stop_ad();
  readVpvVmvPart1Setup();

  readVpvPart2Conversion();

  readVpvVmvPart3PeripheralOff();

  return ADC_CORRECTED_15REF(readVpvVmvPart4GetResult());
}

/**
 * @brief Reads Main valve voltage
 * OBSOLETE, use readVpv shown above!  We no longer have a direct connection to
 * MV pin in order to read with ADC.
 * @return the obtained AD value, 12 bit resolution (0..4092)
 */

uint16_t readVmv2_5(void)
{
  /// AD configuration:
  /// - ADC10CTL0: internal reference 1.5v,
  ///   sample and hold time 16 x ADC clock,
  ///   multiple sample and conversion on,
  ///   ADC on,
  ///   reference generator on,
  /// - ADC10CTL1: AD channel = Vpv, repeat-single-channel mode
  /// - ADC10DTC1: number of conversions = @ref DTC_READ_CNT
  // ADC10CTL0 = SREF_1 | ADC10SHT_2 | MSC | ADC10ON | REFON | REF2_5V;
  // dtc_ad(ADC10_VPV);
  // stop_ad();
  //  Part 1
  REF_2_5V_ON;
  ADCCTL0 = ADCSHT_3 | ADCMSC | ADCON;
  ADCCTL1 = ADCSHS_0 | ADCSHP | ADCDIV_0 | ADCSSEL_0;
  ADCCTL2 = ADCPDIV_0 | ADCRES_2;

  // Part 2
  ConvertAdChannel(ADCSREF_1 | ADC12_VMV);

  // Part 3
  REF_OFF;

  // Part 4
  return ADC_CORRECTED_25REF(readVpvVmvPart4GetResult());
}

/**
* @brief Reads damper open monitor voltage
* @return the obtained AD value, 12 bit resolution (0..4092)

* Function called at various points in execution to read
* damper open state. It reads the DOM AD channel to obtain a 12 bit value
*/
#ifdef DAMPER
uint16_t readVdom(void)
{
  REF_1_5V_ON;

  ADCCTL0 = ADCSHT_4 | ADCMSC | ADCON;
  ADCCTL1 = ADCSHS_0 | ADCSHP | ADCDIV_0 | ADCSSEL_0;
  ADCCTL2 = ADCPDIV_0 | ADCRES_2;

  ADCMCTL0 = ADCSREF_1 | ADC12_DOM;

  while (!REF_GENRDY)
    ;
  const uint16_t res = ADC_CORRECTED_15REF(ConvertAd()); // do conversion
  REF_OFF;

  return res;
}
#endif

/**
* @brief Reads motor capacitor voltage
* @return the obtained AD value, 12 bit resolution (0..4092)

* Function called at various points in execution to read
* motor capacitor voltage. It reads the MCAP AD channel to obtain a 12 bit value
*/
uint16_t readVmcap(void)
{
  REF_2_0V_ON;

  ADCCTL0 = ADCSHT_4 | ADCMSC | ADCON;
  ADCCTL1 = ADCSHS_0 | ADCSHP | ADCDIV_0 | ADCSSEL_0;
  ADCCTL2 = ADCPDIV_0 | ADCRES_2;

  ADCMCTL0 = ADCSREF_1 | ADC12_MCAP;

  while (!REF_GENRDY)
    ;
  const uint16_t res = ADC_CORRECTED_20REF(ConvertAd()); // do conversion
  REF_OFF;

  return res;
}

uint8_t IsSafetySwitchShorted(void)
{
  /// Loop for @ref CG_PP_READ_MAX times. For each read, check to see if the
  /// reading indicates that the PV voltage has fallen below
  /// @ref VPV_MAX_OFF_CP_TEST millivolts. If it does so before the looping is
  /// completed, return false to indicate a passed test and break.
  /// Otherwise, return true to indicate that the charge pump FET is shorted.
  // WEAK: Voltage on FET gate drops faster on Barrel. To be verified...
  int8_t  i      = CG_PP_READ_MAX;
  uint8_t result = true;

  readVpvVmvPart1Setup();

  while (i-- > 0)
  {
    // FVS_DBG_ONE_TGL;
    readVpvPart2Conversion();

    const uint16_t vpvReading = ADC_CORRECTED_15REF(readVpvVmvPart4GetResult());
    if (vpvReading < AD_VPV(VPV_MAX_OFF_CP_TEST))
    {
      result = false;
      break;
    }
  }
  readVpvVmvPart3PeripheralOff();
  return result;
}
/**
 * @brief Clears out AdData buffer used to store multiple AD readings
 */
static void ClearAdData(void)
{
  /// This function just calls @ref memset on AdData array.
  memset(AdData, 0, sizeof(AdData));
}

/**
 * @brief Performs n consecutive readings from specified AD channel
 * @param adcmCtl0 AD channel to be read and reference setting per ADCMCTL0 reg
 * @warning ADC must be already configured before calling this function
 */
#if (DTC_READ_CNT != 4)
#error "Supported DTC_READ_CNT count is only 4!"
#endif

#if (DTC_OUTPUT_CNT != 1)
#error "Supported DTC_OUTPUT_CNT count is only 1!"
#endif

static void ConvertAdChannel(uint16_t adcmCtl0)
{
  ADCMCTL0 = adcmCtl0; // set channel and reference
  ADCIV    = 0;        // clear all pending interrupts
  // if ADCSREF set to ADCSREF_1 wait for reference to settle
  // Note: Not generic! ADCSREF_5 not tested.
  if ((adcmCtl0 & ADCSREF) == ADCSREF_1)
  {
    while (!REF_GENRDY)
      ; // wait for internal reference (TODO 100us)
  }

  //    uint16_t count = DTC_READ_CNT;
  //    while(count > 0)
  //    {
  //        AdData[--count] = ConvertAd();   // store data
  //    }

  AdData[0] = ConvertAd(); // store data
  AdData[1] = ConvertAd();
  AdData[2] = ConvertAd();
  AdData[3] = ConvertAd();
  ADC12_STOP; // stop ADC by clearing ADCENC
}

/**
 * @brief Performs n consecutive readings of Pot and UTS/LTS sensors
 * @warning ADC must be already configured before calling this function
 */
static void ConvertAdPotAndSensors(void)
{
  uint16_t count = DTC_READ_CNT * DTC_CHANNEL_CNT;
  ADCIV          = 0; // clear all pending interrupts
  while (count > 0)
  {
    ADCMCTL0        = ADCSREF_0 | ADC12_POT; // set channel 2 and reference
    AdData[--count] = ADC_CORRECTED_15REF(ConvertAd());                  // store data
    ADC12_STOP;                              // clear ADCENC to change channel
    ADCMCTL0        = ADCSREF_0 | ADC12_LTS; // set channel 1
    AdData[--count] = ADC_CORRECTED_15REF(ConvertAd());
    ADC12_STOP;
    ADCMCTL0        = ADCSREF_0 | ADC12_UTS; // set channel 0
    AdData[--count] = ADC_CORRECTED_15REF(ConvertAd());
    ADC12_STOP;
  }
}

/**
 * @brief Returns the 12bit sum of the collected A/D readings.
 */
static uint16_t find_sum12b(void)
{
  /// Adds first DTC_READ_CNT numbers in global DTC buffer AdData
  /// and returns the result (the sum).

  //    uint16_t *dPtr = &AdData[0];
  //    uint16_t return_val = 0;
  //    uint16_t n = DTC_READ_CNT;
  //    do
  //    {
  //        return_val += *dPtr++;
  //    }
  //    while (--n > 0);

  uint16_t return_val = AdData[0] + AdData[1] + AdData[2] + AdData[3];
  /// Sum 12bit * DTC_READ_CNT (4), Output 12bit * DTC_OUTPUT_CNT (1)
  /// Convert sum (14bit) to 12bit with rounding
  return (return_val + 2) / 4;
}

/**
 * @brief Returns the 14bit sum of the collected A/D readings.
 */
static uint16_t find_sum14b(void)
{
  /// Adds first DTC_READ_CNT numbers in global DTC buffer AdData
  /// and returns the result (the sum).

  //    uint16_t *dPtr = &AdData[0];
  //    uint16_t return_val = 0;
  //    uint16_t n = DTC_READ_CNT;
  //    do
  //    {
  //        return_val += *dPtr++;
  //    }
  //    while (--n > 0);

  uint16_t return_val = AdData[0] + AdData[1] + AdData[2] + AdData[3];
  /// Sum 12bit * DTC_READ_CNT (4)
  return return_val;
}

/**
 * @brief Returns the sum of DTC_READ_CNT A/D readings collected from
 *   a one channel in 3-channel DTC mode.
 * @param channel the number of the channel to be processed (0, 1 or 2)
 */
static uint16_t alternate_sum12b(uint16_t channel)
{
  /// This is different from find_sum12b in that
  /// it takes a starting point (channel) and increments by
  /// three each time.
  /// Parameter @ref channel: per @ref ConvertAdPotAndSensors implementation

  uint16_t return_val = 0;
  do
  {
    return_val += AdData[channel];
    channel += DTC_CHANNEL_CNT;
  } while (channel < (DTC_CHANNEL_CNT * DTC_READ_CNT));

  /// Sum 12bit * DTC_READ_CNT (4), Output 12bit * DTC_OUTPUT_CNT (1)
  /// Convert sum (14bit) to 12bit
  return return_val >> 2;
}

/**
* @brief Reset Flame out detection.

* Function is called when Pilot valve is proved to be off to reset
* flame out detection algorithm.
*/
void FlameOutClear(void)
{
  /// Clear the first record in VtpHistory13b (flame history)
  /// to make @ref FlameOutDetect reset the whole flame history.
  VtpHistory13b[0] = 0;
  /// Clear the 3-minute flame out timer to indicate we are not in
  /// flame out delay.
  FlameOutTimer = 0;
}

/**
 * Temporary calculation used during Flame out detection.
 * Calculates the value of Vtp drop used to detect flame out.
 * In Off mode the flame out detection is more sensitive, because the
 * minimum drop is just half the value in normal run mode.
 * @param vtp input value.
 * @return @a vtp or @a vtp / 2 if device is in Off Mode.
 */
static uint16_t VtpDrop(uint16_t vtp)
{
  if (SystemOffTimer > 0)
  {
    vtp >>= 1; // 12.5 / 2 = 6.25%
  }
  return (vtp);
}
//@}

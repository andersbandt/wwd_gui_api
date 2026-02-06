

# import needed modules
from pprint import pprint
from scipy.stats import linregress


# import user created modules
from common import plotter


####################################
###   STATS analysis    ############
####################################

def calculate_statistics(x_arr, y_arr):
    # Calculate linear regression parameters
    slope, intercept, r_value, p_value, std_err = linregress(x_arr, y_arr)

    # Calculate predicted values using the linear model
    predicted_values = slope * x_arr + intercept
    pprint(predicted_values)

    # Calculate residuals (difference between observed and predicted values)
    residuals = y_arr - predicted_values

    return {
        "slope": slope,
        "intercept": intercept,
        "r": r_value,
        "standard error": std_err,
        "residuals": residuals
    }


# get linear fit in the form of y = m*x + b
def linear_fit(x_arr, y_arr):
    # Calculate linear regression parameters
    slope, intercept, r_value, p_value, std_err = linregress(x_arr, y_arr)
    print(f"y=mx+b <<< --- >>>   {slope}*[x] + {intercept}")

    stats = calculate_statistics(x_arr, y_arr)

    # make a plot of residuals
    plotter.time_plot(
        x_arr,
        stats["residuals"],
        "Time series",
        "Linear best fit residuals"
    )

    return stats
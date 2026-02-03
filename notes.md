# Development Notes & Recommendations

*Generated: 2025-02-03*

---

## 🔥 **HIGH PRIORITY - Critical for Open Source Release**

### 1. **Add MIT License File**
- **Why**: README references it but file doesn't exist
- **Action**: Create `LICENSE` file with MIT license text
- **Time**: 5 minutes

### 2. **Clean Requirements.txt**
- **Issues**:
  - `libusb` shouldn't be in requirements.txt (system package)
  - `usb` and `pyusb` are redundant (keep `pyusb`)
  - Missing version pinning (risky for reproducibility)
- **Action**:
  ```txt
  pyserial>=3.5
  matplotlib>=3.5.0
  pandas>=1.4.0
  numpy>=1.21.0
  scipy>=1.7.0
  pyusb>=1.2.1
  PyVISA>=1.12.0
  pyvisa-py>=0.5.3
  ```
- **Time**: 10 minutes

### 3. **Add .gitignore**
- **Why**: Prevent committing sensitive/temporary files
- **Should ignore**:
  - `__pycache__/`, `*.pyc`, `*.pyo`
  - `.vscode/`, `.idea/`
  - `data/*.csv`, `data/*.log` (user data)
  - `config/ports_used.xml` (machine-specific)
  - `*.egg-info/`, `dist/`, `build/`
- **Time**: 5 minutes

### 4. **Fix TODO: USB Connection After Startup**
- **Location**: `guiTab_1_mainDashboard.py:53`
- **Issue**: USB doesn't connect properly after program startup
- **Impact**: Main dashboard functionality
- **Time**: 30 minutes

---

## 🎯 **MEDIUM PRIORITY - Quality & User Experience**

### 5. **Standardize Dynamic Padding**
- **Locations**:
  - `guiTab_6_FG.py:63` - "need to add dynamic padding"
  - `guiTab_8_LOG.py:78` - "implement dynamic padding"
- **Why**: Inconsistent UI on different screen sizes
- **Action**: Create helper function in `gui_class.py` for dynamic padding based on `theme_config`
- **Time**: 1 hour

### 6. **Remove Hardcoded Values**
- **Found 10 instances** with `tag:HARDCODE`
- **Priority fixes**:
  - `gui_driver.py:49` - Hardcoded tab count `range(1, 10)`
  - `guiTab_3_XDS110.py:66` - Hardcoded config file path
  - `guiTab_4_USB.py` - Hardcoded data paths and commands
- **Action**: Move to config file or constants
- **Time**: 2 hours

### 7. **Add Graph UI Improvements**
- **Location**: `guiTab_9_GRAPH.py:109, 119`
- **Issues**:
  - "make it more intuitive on what is labeling vs data specific"
  - "title text box might have to be bigger"
- **Action**:
  - Add section separators (ttk.Separator)
  - Make title box auto-expand
  - Add tooltips for clarity
- **Time**: 1 hour

### 8. **Fix Threading Issue in Logger**
- **Location**: `guiTab_8_LOG.py:513`
- **Issue**: "do I have to stop the thread here?"
- **Why**: Potential resource leak
- **Action**: Properly stop/join thread in `stop_record()`
- **Time**: 30 minutes

### 9. **Handle E3640A Output Flickering**
- **Location**: `guiTab_8_LOG.py:816`
- **Issue**: "E3640A turns off output briefly during stimulus measurement"
- **Impact**: Measurement accuracy
- **Action**: Investigate PS behavior, add delay or change measurement approach
- **Time**: 1 hour

---

## 💡 **NICE TO HAVE - Feature Enhancements**

### 10. **Add Screenshot/Demo to README**
- **Why**: Visual appeal, helps users decide to try it
- **Action**: Take 3-4 screenshots of main features, add to README
- **Time**: 30 minutes

### 11. **Create CONTRIBUTING.md**
- **Why**: README mentions it but doesn't exist
- **Action**: Document:
  - How to add new equipment drivers
  - Code style guidelines
  - Testing requirements
  - Pull request process
- **Time**: 1 hour

### 12. **Add Unit Tests**
- **Current**: Only 1 test file in submodule
- **Priority test coverage**:
  - `logger.py` - StimulusGenerator, CSV building
  - `plotter.py` - plot_multi_file_data
  - `common/` utilities
- **Framework**: `pytest`
- **Time**: 4-6 hours (start with critical paths)

### 13. **Improve Serial Timing Logging**
- **Location**: `guiTab_8_LOG.py:523`
- **Issue**: "needs to know if we want serial data to base timing off UART output"
- **Feature**: Option to trigger recording on serial data arrival
- **Time**: 2 hours

### 14. **Add Connection Status Detection**
- **Location**: `gui_class.py:281`
- **Issue**: "need to pass in `status_cmd` to detect connection status"
- **Feature**: Auto-detect when equipment disconnects
- **Time**: 1-2 hours

---

## 🧹 **CODE CLEANUP - Technical Debt**

### 15. **Phase Out ttk.Button Usage**
- **Location**: `guiTab_1_mainDashboard.py:125`
- **Why**: Inconsistent with themed buttons
- **Action**: Replace with `tk.Button` + theme colors
- **Time**: 30 minutes

### 16. **Consolidate Analysis Modules**
- **Location**: `analysis/` directory (7 files)
- **Issue**: Appears underutilized, unclear purpose
- **Action**:
  - Document what each does
  - Consider if they should be in main app or separate scripts
  - Move IMU-specific code (`imu/`) if not used
- **Time**: 1 hour review

### 17. **Add Error Handling Improvements**
- **Found**: 3 empty `except: pass` blocks
- **Action**: Add logging/error messages
- **Time**: 1 hour

### 18. **Create Equipment Driver Documentation**
- **Why**: Make it easy to add new equipment
- **Action**:
  - Document base class usage
  - Provide template
  - Examples from existing drivers
- **Time**: 2 hours

---

## 📊 **METRICS & INSIGHTS**

**Codebase Stats:**
- ~6,000 lines of Python code (excluding submodule)
- 9 GUI tabs
- 10+ equipment drivers
- 10 TODOs/FIXMEs
- 10 hardcoded values
- Only 1 test file (needs more!)

**Architecture Strengths:**
- ✅ Good separation of concerns (gui/, common/, EEequipment/)
- ✅ Themed UI system
- ✅ Command registry pattern
- ✅ Named tuples for clarity

**Architecture Opportunities:**
- ⚠️ Limited test coverage
- ⚠️ Some hardcoded values
- ⚠️ Threading management could be cleaner
- ⚠️ Missing type hints (Python 3.8+ feature)

---

## 🎯 **RECOMMENDED ACTION PLAN**

### **Week 1: Pre-Release Cleanup**
1. Add LICENSE file (5 min)
2. Fix requirements.txt (10 min)
3. Add .gitignore (5 min)
4. Add screenshots to README (30 min)
5. Fix USB connection after startup (30 min)

**Total: ~1.5 hours**

### **Week 2: Quality Improvements**
1. Standardize dynamic padding (1 hr)
2. Remove hardcoded values (2 hrs)
3. Fix threading issue (30 min)
4. Add graph UI improvements (1 hr)

**Total: ~4.5 hours**

### **Week 3: Documentation & Testing**
1. Create CONTRIBUTING.md (1 hr)
2. Add equipment driver docs (2 hrs)
3. Start unit tests (4 hrs - ongoing)

**Total: ~7 hours**

### **Week 4+: Feature Enhancements**
- Serial timing trigger
- Connection status detection
- Advanced analysis tools
- Additional equipment support

---

## 🚀 **MY TOP 3 RECOMMENDATIONS FOR RIGHT NOW**

If you only have time for 3 things before open sourcing:

1. **Add LICENSE file** (5 min) - Legally required
2. **Fix requirements.txt + add .gitignore** (15 min) - Professional basics
3. **Add 2-3 screenshots to README** (30 min) - Huge impact on adoption

**Total: ~50 minutes for massive credibility boost**

---

## 📝 **TODO LIST**

### Outstanding TODOs in Code:
- [ ] `guiTab_1_mainDashboard.py:53` - USB connection after startup
- [ ] `guiTab_1_mainDashboard.py:125` - Phase out ttk.Button usage
- [ ] `guiTab_6_FG.py:63` - Add dynamic padding
- [ ] `guiTab_8_LOG.py:78` - Implement dynamic padding
- [ ] `guiTab_8_LOG.py:513` - Stop thread properly
- [ ] `guiTab_8_LOG.py:523` - Serial timing trigger
- [ ] `guiTab_8_LOG.py:816` - E3640A output flickering
- [ ] `guiTab_9_GRAPH.py:109` - Improve labeling UI clarity
- [ ] `guiTab_9_GRAPH.py:119` - Make title box dynamic
- [ ] `gui_class.py:281` - Connection status detection

### Hardcoded Values to Fix:
- [ ] `guiTab_3_XDS110.py:66` - Config file path
- [ ] `guiTab_3_XDS110.py:291` - Sleep timer value
- [ ] `guiTab_4_USB.py:127` - Command string
- [ ] `guiTab_4_USB.py:203,209` - Data paths
- [ ] `guiTab_8_LOG.py:553` - Enum mapping
- [ ] `gui_driver.py:35` - Config file path
- [ ] `gui_driver.py:49` - Tab count range
- [ ] `gui_driver.py:125` - Autoconnect list size
- [ ] `gui_driver.py:180` - Unknown hardcode

---

## 🎓 **LESSONS LEARNED / DESIGN PATTERNS**

### What's Working Well:
1. **ClassController Pattern** - Centralized equipment management
2. **Named Tuples** - Self-documenting file data structures
3. **Themed UI** - Consistent look across application
4. **StimulusConfig Reuse** - DRY principle applied successfully
5. **Command Registry** - Flexible equipment command management

### Areas for Improvement:
1. **Test Coverage** - Critical for reliability and refactoring confidence
2. **Type Hints** - Would catch bugs early and improve IDE support
3. **Configuration Management** - Too many hardcoded paths
4. **Error Handling** - Some exceptions silently swallowed
5. **Documentation** - Code is fairly self-explanatory but lacks docstrings in places

---

## 💭 **FUTURE VISION / FEATURE IDEAS**

### Short Term (3-6 months):
- [ ] Plugin system for community equipment drivers
- [ ] Automated report generation (PDF)
- [ ] FFT/frequency analysis tools
- [ ] Oscilloscope integration
- [ ] Remote control API

### Long Term (6-12+ months):
- [ ] Web interface option (Flask/FastAPI backend)
- [ ] Database storage option (SQLite/PostgreSQL)
- [ ] Multi-user collaboration features
- [ ] Cloud data sync (optional)
- [ ] Mobile app for monitoring

### Community Requests (track via GitHub Issues):
- TBD based on user feedback

---

## 🔗 **USEFUL RESOURCES**

### For Contributors:
- PyVISA docs: https://pyvisa.readthedocs.io/
- Tkinter best practices: https://tkdocs.com/
- Testing with pytest: https://docs.pytest.org/

### For Users:
- SCPI commands: https://en.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments
- Lab automation best practices: TBD

---

*This is a living document. Update as issues are resolved and new priorities emerge.*

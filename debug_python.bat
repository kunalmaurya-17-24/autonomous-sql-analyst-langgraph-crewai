@echo off
echo STARTING_BATCH_EXECUTION
dir .venv\Scripts\python.exe
.venv\Scripts\python.exe -c "print('PYTHON_IS_WORKING')"
if %errorlevel% neq 0 echo PYTHON_FAILED_WITH_ERRORLEVEL_%errorlevel%
echo FINISHED_BATCH_EXECUTION

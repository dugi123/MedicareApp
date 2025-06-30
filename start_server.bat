@echo off
echo Starting Medicare Project Development Server...
echo.
echo Step 1: Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Step 2: Starting livereload server (in a new window)...
start cmd /k "cd C:\Users\NIMADITH\Desktop\MedicareApp\medicare_project && ..\venv\Scripts\activate.bat && python manage.py livereload"

echo.
echo Step 3: Starting Django development server...
cd medicare_project
python manage.py runserver

echo.
echo Server stopped. Press any key to exit...
pause > nul

# Downtime Tracker

Downtime Tracker for Lesira-Teq

## Set up

On terminal run:

```
"PATH-TO-PYTHON-3.12(for windows 8+)" -m venv venv.12
```

```
"PATH-TO-PYTHON-3.8(for windows 7 and below)" -m venv venv.8
```

```
venv.12/Scripts/python.exe -m pip install -r requirements.txt
```

```
venv.8/Scripts/python.exe -m pip install -r requirements.txt
```

## Export

For Python 3.8

```
venv.8/Scripts/python.exe -m PyInstaller --onefile --windowed --icon=assets/icon.ico --add-data "assets/icon.ico;assets" --add-data "data/operators.csv;data" --distpath "dist.8" main.py
```

For Python 3.12

```
venv.12/Scripts/python.exe -m PyInstaller --onefile --windowed --icon=assets/icon.ico --add-data "assets/icon.ico;assets" --add-data "data/operators.csv;data" --distpath "dist.12" main.py
```

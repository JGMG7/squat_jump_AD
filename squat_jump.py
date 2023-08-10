#Python code to Squat Jump evaluation
#Journal Name : IOSR Journal of Sports and Physical Education
#Article Title : Low cost Device for Vertical Jump Measurement in Sports Training
#Authors: Meléndez-Gallardo, José; Hernández-Garcia, Facundo
#Grupo de Investigación Biofísica y Bioquímica del Ejercicio,
#Instituto Superior de Educación Física (ISEF)-Centro Universitario Regional del Este (CURE),
#Universidad de la República (Udelar), Uruguay.

import datetime
import sys
import time
import csv
from math import sqrt
import numpy as np
from statistics import median
from Adafruit_BNO055 import BNO055

# Initialize BNO055 sensor object with serial port and reset pin settings
bno = BNO055.BNO055(serial_port='/dev/serial0', rst=18)

# Set the update frequency for the sensor readings
BNO_UPDATE_FREQUENCY_HZ = 1000

# Check if the program was launched with the '-v' flag for verbose logging
if len(sys.argv) == 2 and sys.argv[1].lower() == '-v':
    logging.basicConfig(level=logging.DEBUG)

# Initialize the BNO055 sensor
if not bno.begin():
    logging.error('Failed to initialize BNO055! Is the sensor connected?')
    sys.exit(1)

# Get system status, self-test result, and error
status, self_test, error = bno.get_system_status()

# Print the system status and self-test result
print('System status: {0}'.format(status))
print('Self-test result (0x0F is normal): 0x{0:02X}'.format(self_test))

# Check for system error and exit if there is an error
if status == 0x01:
    logging.error('System error: {0}'.format(error))
    logging.error('See datasheet section 4.3.59 for the meaning.')
    sys.exit(1)

# Get revision information for accelerometer, magnetometer, gyro, etc.
sw, bl, accel, mag, gyro = bno.get_revision()
print('Accelerometer ID:   0x{0:02X}'.format(accel))

# Calibration
# Get calibration status for accelerometer, magnetometer, and gyroscope
accel = bno.get_calibration_status()

# Reset the calibration values to default (set all to 255)
bno.set_calibration([0xFF]*22)

# Print accelerometer calibration status
print('Accel_cal={0} '.format(accel))

# Print a message to indicate that BNO055 data reading has started
print('Reading BNO055 data, press Ctrl-C to quit...')

# Input variables
nombre = input("Enter the name: ")
edad = float(input("Enter age: "))
masa = float(input("Enter weight in Kg: "))
a_cuerpo = float(input("Enter body height in cm: "))
h = float(input("Enter length of lower limb in cm: "))
hs = float(input("Enter initial height in cm: "))

# Variables from cm to meters
a_cuerpo2 = a_cuerpo / 100
h2 = h / 100
hs2 = hs / 100

# Function to calculate height based on sensor measurements
def calculate_height(x, y, z, gx, gy, gz, window):
    # Calculations to determine the height
    height = (x**2 + y**2 + z**2)**0.5 + (gx**2 + gy**2 + gz**2)**0.5
    # Return the calculated height
    return height

# Lists to store sensor measurements
listaY, listaZ, listaX, listaTiempo, lista_inicio = [], [], [], [], [0]

# New lists to store smoothed measurements
listaY_suavizada, listaX_suavizada = [], []

# Moving average window size
window = 7

# Thresholds for acceleration
umbral_max = 9
umbral_min = 5

# Flag to track ascending motion
ascendente = False

# Variable to store the previous y value
ultimo_y = 0

# Main loop for sensor measurements
while True:
    # Get sensor measurements
    x, y, z = bno.read_linear_acceleration()
    gx, gy, gz = bno.read_gyroscope()
    
    # Check for ascending motion
    if y > umbral_max and y > ultimo_y and y > umbral_min:
        ascendente = True
        if umbral_max > 2:
            umbral_max = 2
    ultimo_y = y

    # Store ascending data
    if ascendente and y > umbral_max:
        lista_inicio.append(time.perf_counter_ns())
        listaY.append(y)
        listaZ.append(z)
        listaX.append(x)

    # Calculate data when ascending motion ends
    if ascendente and y <= umbral_max:
        ascendente = False
        if len(lista_inicio) > 1:
            tiempo = round((lista_inicio[-1] - lista_inicio[1]) / 1e9, 3)
            listaTiempo.append(tiempo)

        # Sort lists by Y-axis acceleration
        listaY, listaX, listaZ = map(list, zip(*sorted(zip(listaY, listaX, listaZ))))

        # Apply moving average to acceleration lists for X, Y, and Z axes
        y_suavizada = np.convolve(listaY[-window:], np.ones((window,))/window, mode='valid')
        x_suavizada = np.convolve(listaX[-window:], np.ones((window,))/window, mode='valid')
        z_suavizada = np.convolve(listaZ[-window:], np.ones((window,))/window, mode='valid')

        # Calculate mean acceleration
        a_m = round(np.median(y_suavizada), 3)

        # Calculate height (Y-axis)
        seg = round((tiempo), 3)
        alt = round(((listaY[-1] * seg**2) / 2) * 100, 3)

        # Calculate ascending time
        tiempo_ascenso = round(np.sqrt((2 * (alt/100)) / y_suavizada[-1]), 3)

        # Calculate distance traveled (X-axis)
        dist = round(((x_suavizada[-1] * tiempo_ascenso**2) / 2) * 100, 3)

        # Calculate mean and standard deviation of height
        altura_mean = np.mean(listaY[-window:])
        altura_std = np.std(listaY[-window:])

        # Define upper and lower limits for acceptable values
        altura_upper_limit = altura_mean + 3 * altura_std
        altura_lower_limit = altura_mean - 3 * altura_std

        # Filter out outliers from the height list
        listaY_filtrada = [y for y in listaY[-window:] if (y >= altura_lower_limit) and (y <= altura_upper_limit)]

        # Replace the height list with the filtered list
        listaY[-window:] = listaY_filtrada

        if y_suavizada[-1] > 0:
            # Calculate height using three axes and gyroscope
            altura_calculada = round(calculate_height(x_suavizada[-1], y_suavizada[-1], z_suavizada[-1], gx, gy, gz, window), 3)
        else:
            # If acceleration is negative, set calculated height to zero
            altura_calculada = 0

        # Force, velocity, power, and work calculations
        altura_metros = altura_calculada / 100
        g = 9.80665
        hpo = h2 - hs2
        imc = round((float(masa / a_cuerpo2**2)), 2)
        fuerza = round(masa * g * ((altura_metros/hpo) + 1), 3)
        velocidad = round(np.sqrt((g * altura_metros) / 2), 3)
        potencia = round((velocidad * fuerza), 3)
        wt = round(masa * g * (hpo + altura_metros), 3)

        # Print the results
        print("Height:", altura_calculada, "cm")
        print("Ascent time:", tiempo_ascenso, "s")
        print("Maximum acceleration:", listaY[-1], "m/s^2")
        print("Force:", fuerza, "N")
        print("Velocity:", velocidad, "m/s")
        print("Power:", potencia, "W")
        print("Work:", wt, "J")
        print("IMC:", imc)
        print("*" * 60)

        # Delay to update sensor measurements
        time.sleep(1 / BNO_UPDATE_FREQUENCY_HZ)
        
        # Write data to a CSV file
        with open('datos.csv', 'a') as f:
            csv.writer(f).writerows(zip([nombre], [edad], [masa], [a_cuerpo], [altura_calculada], [tiempo_ascenso], [listaY[-1]],
                                        [fuerza], [velocidad], [potencia], [wt], [imc]))
        
        # Clear the lists for the next iteration
        listaY, listaZ, listaX, listaTiempo, lista_inicio = [], [], [], [], [0]
        
        # Ask if the program should continue or stop
        conti = input("Press ENTER to continue or S to stop the program: ")
        if conti.lower() == "s":
           break

import time
import configparser
from sense_hat import SenseHat
from influxdb import InfluxDBClient
from datetime import datetime

# Configuration File
CONFIG_FILE = "settings.conf"

#Sense HAT
sense = SenseHat()
sense.set_rotation(180)
sense.show_message("Starting...")

def get_reading(config):
    # InfluxDB connection info
    host = config['influxdb_settings']['host']
    port = config['influxdb_settings']['port']
    user = config['influxdb_settings']['user']
    password = config['influxdb_settings']['password']
    dbname = config['influxdb_settings']['dbname']
    measurement = config['sensor_settings']['measurement']
    location = config['sensor_settings']['location']

    # Create the InfluxDB client object
    client = InfluxDBClient(host, port, user, password, dbname)

    humidity = sense.get_humidity()
    pressure = sense.get_pressure()

    if humidity is None:
        print ("Humidity is null, possibly an err code.")
        return
    if humidity > 100 or humidity < 0 :
        print ("Humidity is abnormal, possibly an err code : " +  humidity)
        return

    celcius = sense.get_temperature()
        
    # Add Farhenheit for us 'Mericans
    farhenheit = celcius * 9 / 5 + 32

    # Structure Timestamp to UTC
    current_time = time.gmtime()
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', current_time)

    #Dew Point
    dew_point = celcius - ((100 - humidity) / 5)

    #Heat Index
    heat_index = - 42.379 + (2.04901523 * farhenheit) + (10.14333127 * humidity) - (0.22475541 * farhenheit * humidity) - (6.83783*(10**-3)*farhenheit**2) - (5.481717 * (10**-2) * humidity**2) + (1.22874 * (10**-3) * farhenheit**2 * humidity) + (8.5282*(10**-4) * farhenheit * humidity**2) - (1.99*(10**-6) * farhenheit**2 * humidity**2)

    acceleration = sense.get_accelerometer_raw()

    # Structure the data for write
    data = [
        {
            "measurement": measurement,
            "tags": {
                "location": location,
            },
            "time": timestamp,
            "fields": {
                "temperature_c": celcius,
                "temperature_f": farhenheit,
                "humidity": humidity,
                "pressure": pressure,
                "x": acceleration['x'],
                "y": acceleration['y'],
                "z": acceleration['z'],
                "dew_point": dew_point,
                "heat_index_f": heat_index,
                "heat_index_c": (heat_index - 32) * 5/9 
            }
        }
    ]

    # Write it!
    client.write_points(data)

    # Return the temperature value.
    return data

def read_config():
    cfg = configparser.ConfigParser()

    # Read the config
    cfg.read(CONFIG_FILE)

    # Read the Values from the config
    config = {section: {k: v for k, v in cfg.items(section)} for section in cfg.sections()}

    # Return the config
    return config

def main():
    # Initial threshold counter.
    threshold_counter = []

    # Read the config
    config = read_config()

    direction = None

    while True:
        # Get the reading and send to Influx
        reading = get_reading(config)[0]
        
        for event in sense.stick.get_events():
            direction = event.direction # , event.action

        if direction == "up":
            sense.show_message(str(round(reading["fields"]["temperature_c"], 2)) + " C "
                + str(round(reading["fields"]["humidity"], 2)) + " % " +
                str(round(reading["fields"]["pressure"], 2)) + " mBar"
            )
        elif direction == "down":
            now = datetime.now()
            sense.show_message(now.strftime("%-I:%M %p"))
        elif direction == "right":
            direction = None
            sense.show_message("Screen Disabled")
        elif direction == "left":
            sense.show_message(
                str(round(reading["fields"]["x"], 2)) + " " +
                str(round(reading["fields"]["y"], 2)) + " " +
                str(round(reading["fields"]["z"], 2)) + " "
            )


        # Loop Complete - Sleep for 10 seconds
        time.sleep(15)

if __name__ == '__main__':
    main()

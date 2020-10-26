import time
import requests
import configparser
import Adafruit_DHT
from influxdb import InfluxDBClient

# Configuration File
CONFIG_FILE = "settings.conf"

def get_reading(config):
    # InfluxDB connection info
    host = config['influxdb_settings']['host']
    port = config['influxdb_settings']['port']
    user = config['influxdb_settings']['user']
    password = config['influxdb_settings']['password']
    dbname = config['influxdb_settings']['dbname']

    # Create the InfluxDB client object
    client = InfluxDBClient(host, port, user, password, dbname)

    # Sensor details
    #sensor = str(config['sensor_settings']['sensor'])
    sensor = Adafruit_DHT.DHT22
    sensor_gpio = config['sensor_settings']['sensor_gpio_pin']
    measurement = config['sensor_settings']['measurement']
    location = config['sensor_settings']['location']

    humidity, celcius = Adafruit_DHT.read_retry(sensor, sensor_gpio)
    if humidity is None:
        print ("Humidity is null, possibly an err code.")
    if humidity > 100 or humidity < 0 :
        print ("Humidity is abnormal, possibly an err code : " +  humidity)
        return
        
    # Add Farhenheit for us 'Mericans
    farhenheit = celcius * 9 / 5 + 32

    # Structure Timestamp to UTC
    current_time = time.gmtime()
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', current_time)

    #Dew Point
    dew_point = celcius - ((100 - humidity) / 5)

    #Heat Index
    heat_index = - 42.379 + (2.04901523 * farhenheit) + (10.14333127 * humidity) - (0.22475541 * farhenheit * humidity) - (6.83783*(10**-3)*farhenheit**2) - (5.481717 * (10**-2) * humidity**2) + (1.22874 * (10**-3) * farhenheit**2 * humidity) + (8.5282*(10**-4) * farhenheit * humidity**2) - (1.99*(10**-6) * farhenheit**2 * humidity**2)

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

    while True:
        # Get the reading and send to Influx
        current_temperature = get_reading(config)

        # Loop Complete - Sleep for 10 seconds
        time.sleep(5)

if __name__ == '__main__':
    main()

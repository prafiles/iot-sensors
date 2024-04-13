import time
import json
import configparser
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt

import Adafruit_DHT

# Configuration File
CONFIG_FILE = "settings.conf"
client = None

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
        return
    if humidity > 100 or humidity < 0 :
        print ("Humidity is abnormal, possibly an err code : " + str(humidity))
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

    # Return the payload
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
    global client 
    client = mqtt.Client()

    # Set username and password if MQTT broker requires authentication
    client.username_pw_set(config['mqtt_settings']['username'], config['mqtt_settings']['password'])

    # Connect to the broker
    client.connect(config['mqtt_settings']['broker_address'], config['mqtt_settings']['port'])

    
    

    while True:

        try:

            # Get the reading and send to Influx
            data = get_reading(config)
            payload = json.dumps(data)
            # Publish the data to the topic
            client.publish(config['mqtt_settings']['topic'], payload)

        except Exception as e:
            print(e)

        # Loop Complete - Sleep for 10 seconds
        time.sleep(15)

    # Disconnect from the broker
    client.disconnect()

if __name__ == '__main__':
    main()

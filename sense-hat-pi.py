import time
import json
import configparser
from sense_hat import SenseHat
from influxdb import InfluxDBClient
from datetime import datetime
import paho.mqtt.client as mqtt

# Configuration File
CONFIG_FILE = "settings.conf"
client = None

#Sense HAT
sense = SenseHat()
sense.set_rotation(180)
sense.show_message("Starting...")
print("Starting...")

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

    humidity = float(sense.get_humidity())
    pressure = float(sense.get_pressure())

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
                "temperature_c": round(celcius,2),
                "temperature_f": round(farhenheit,2),
                "humidity": round(humidity,2),
                "pressure": pressure,
                "x": acceleration['x'],
                "y": acceleration['y'],
                "z": acceleration['z'],
                "dew_point": round(dew_point,2),
                "heat_index_f": round(heat_index,2),
                "heat_index_c": round((heat_index - 32) * 5/9,2)
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
    global client 
    client = mqtt.Client()

    # Set username and password if MQTT broker requires authentication
    client.username_pw_set(config['mqtt_settings']['username'], config['mqtt_settings']['password'])

    # Connect to the broker
    client.connect(config['mqtt_settings']['broker_address'], int(config['mqtt_settings']['port']))

    direction = None

    while True:
        # Loop Complete - Sleep for 10 seconds
        time.sleep(15)

        # Get the reading and send to Influx
        reading = False
        try:
            reading = get_reading(config)[0]
            payload = json.dumps(reading)
            client.publish(config['mqtt_settings']['topic'] + config['sensor_settings']['location'], payload)
        except Exception as e:
            sense.show_message("Error in reading...")
            print (e)
            continue

        
        for event in sense.stick.get_events():
            direction = event.direction # , event.action

        if direction == "up":
            sense.show_message(str(round(reading["fields"]["temperature_c"], 2)) + " C "
                + str(round(reading["fields"]["humidity"], 2)) + " % " +
                str(round(reading["fields"]["pressure_v2"], 2)) + " mBar"
            )
        elif direction == "down":
            now = datetime.now()
            sense.show_message(now.strftime("%-I:%M%p"))
        elif direction == "right":
            direction = None
            sense.show_message("Screen Disabled")
        elif direction == "left":
            sense.show_message(
                str(round(reading["fields"]["x"], 2)) + " " +
                str(round(reading["fields"]["y"], 2)) + " " +
                str(round(reading["fields"]["z"], 2)) + " "
            )
        print("Loop ended success")
    
    client.disconnect()

if __name__ == '__main__':
    main()

from airflow import DAG
from datetime import timedelta, datetime
from airflow.operators.python import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
import requests
import pandas as pd


api_key = '51309be894f62b47e839f89d861acbee'

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 8),
    'email': ['myemail@domain.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2)
}


def kelvin_to_fahrenheit(temp_in_kelvin):
    temp_in_fahrenheit = (temp_in_kelvin - 273.15) * (9/5) + 32
    return temp_in_fahrenheit


def etl_weather_data():
    combined_df = pd.DataFrame()
    names_of_city = ["Portland", "Seattle", "Houston", "Lagos", "London", "Mumbai", "Beijing"]
    base_url = "https://api.openweathermap.org"    
    for city in names_of_city:
        end_point = "/data/2.5/weather?q=" + city + "&APPID=" + api_key
        full_url = base_url + end_point
        r = requests.get(full_url)
        data = r.json()      
       
       
        city = data["name"]
        weather_description = data["weather"][0]['description']
        temp_farenheit = kelvin_to_fahrenheit(data["main"]["temp"])
        feels_like_farenheit= kelvin_to_fahrenheit(data["main"]["feels_like"])
        min_temp_farenheit = kelvin_to_fahrenheit(data["main"]["temp_min"])
        max_temp_farenheit = kelvin_to_fahrenheit(data["main"]["temp_max"])
        pressure = data["main"]["pressure"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        time_of_record = datetime.utcfromtimestamp(data['dt'] + data['timezone'])
        sunrise_time = datetime.utcfromtimestamp(data['sys']['sunrise'] + data['timezone'])
        sunset_time = datetime.utcfromtimestamp(data['sys']['sunset'] + data['timezone'])

        transformed_data = {"City": city,
                            "Description": weather_description,
                            "Temperature (F)": temp_farenheit,
                            "Feels Like (F)": feels_like_farenheit,
                            "Minimun Temp (F)":min_temp_farenheit,
                            "Maximum Temp (F)": max_temp_farenheit,
                            "Pressure": pressure,
                            "Humidty": humidity,
                            "Wind Speed": wind_speed,
                            "Time of Record": time_of_record,
                            "Sunrise (Local Time)":sunrise_time,
                            "Sunset (Local Time)": sunset_time                        
                            }

        transformed_data_list = [transformed_data]
        df_data = pd.DataFrame(transformed_data_list)
        combined_df = pd.concat([combined_df, df_data], ignore_index=True)        

    now = datetime.now()
    dt_string = now.strftime("%d%m%Y%H%M%S")
    dt_string = 'current_weather_data_' + dt_string
    combined_df.to_csv(f"{dt_string}.csv", index=False)
    # combined_df.to_csv("current_weather_data.csv", index = False)
    output_file = f"/home/ubuntu/{dt_string}.csv"
    return output_file


with DAG('weather_dag',
         default_args=default_args,
         schedule_interval = '@daily',
         catchup=False) as dag:
        
        extract_transform_weather_data = PythonOperator(
        task_id= 'tsk_extract_transform_weather_data',
        python_callable = etl_weather_data
        )
        
        load_to_s3 = BashOperator(
            task_id = 'task_load_to_s3',
            bash_command = 'aws s3 mv {{ ti.xcom_pull("tsk_extract_transform_weather_data")}} s3://weatherairflow',
        )
        
       
        slack_alert = SlackWebhookOperator(
                task_id='slack_alert',
                slack_webhook_conn_id="slack_conn_id",
                trigger_rule='one_failed',
                message="There is an error\n"
                        "DAG name: {{ dag.dag_id }}\n"
                        "Run: {{ run_id }}\n"
                        "url: {{ conf.get('webserver', 'BASE_URL') }}/dags/{{ dag.dag_id }}/grid"
            )      


##### The Other Version of Slack Alerts #####

#slack_fail_alert(context):

#    slack_msg = f"""
#        :x: Task Failed.
#        *Task*: {context.get('task_instance').task_id}
#        *Dag*: {context.get('task_instance').dag_id}
#        *Execution Time*: {context.get('execution_date')}
#        <{context.get('task_instance').log_url}|*Logs*>
#    """

#    slack_alert = SlackWebhookOperator(
#        task_id='slack_fail',
#        slack_webhook_conn_id="slack_conn_id",
#        message=slack_msg,
#        channel="#project-weather-data",
#    )

#    return slack_alert.execute(context=context)
        
        


        
        

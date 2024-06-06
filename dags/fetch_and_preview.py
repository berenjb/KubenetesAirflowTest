import json

from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import pandas as pd
from datetime import datetime, timedelta


def get_data(**kwargs):
    url: str = 'https://raw.githubusercontent.com/airscholar/ApacheFlink-SalesAnalytics/main/output/new-output.csv'
    response = requests.get(url)

    if response.status_code == 200:
        df = pd.read_csv(url, names=['Category', 'Price', 'Quantity'])

        # convert to JSON
        json_data = df.to_json(orient='records')
        kwargs['ti'].xcom_push(key='data', value=json_data)
    else:
        raise Exception(f'Failed to fetch data, status code {response.status_code}')


def preview_data(**kwargs):
    output_data = kwargs['ti'].xcom_pull(key='data', task_ids='get_data')
    print(output_data)
    if output_data:
        output_data = json.loads(output_data)
    else:
        raise ValueError('No data received from XCom')

    ## Create data from JSON

    df = pd.DataFrame(output_data)

    # compute total sales

    df['Total Sales'] = df['Price'] * df['Quantity']

    df = df.groupby('Category', as_index=False).agg({"Quantity": "sum", "Total Sales": "sum"})

    # sort by total sales

    df = df.sort_values(by='Total Sales', ascending=False)

    print(df[['Category', 'Total Sales']]).head(20)


default_args = {
    'owner': 'Barron',
    'start_date': datetime(2024, 6, 5),
    'catchup': False
}

dag = DAG(
    'fetch_and_preview',
    default_args=default_args,
    schedule=timedelta(days=1)
)

get_data_from_url = PythonOperator(
    task_id='get_data',
    python_callable=get_data,
    dag=dag
)

preview_data_from_url = PythonOperator(
    task_id='preview_data',
    python_callable=preview_data,
    dag=dag
)


get_data_from_url >> preview_data_from_url
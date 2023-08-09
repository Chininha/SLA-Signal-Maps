import streamlit as st
from figures import *
from figures import sla_indicator_chart, sla_last_30days, rssi_last_30days, transmissions, \
    metrics_boxplot, battery_voltage_last30days, recent_reading, sla_per_city, sla_bat_rssi_all_project
from queries import querie_builder, data_treatement
from datetime import datetime

def sla_overview(results:querie_builder.Queries, main_data) -> None:
    metrics_data_30days = querie_builder.Queries.load_imporant_data(queries_responses=results, specific_response='SLA_OVER_TIME_ALL_UNITS')
    df_all_unit_services = main_data
    df_recent_readings = querie_builder.Queries.load_imporant_data(queries_responses=results, specific_response='RECENT_READINGS')
    df_daily_transmissions = querie_builder.Queries.load_imporant_data(queries_responses=results, specific_response='DAILY_TRANSMISSIONS')
    df_daily_transmissions.snapshot_date = df_daily_transmissions.snapshot_date.apply(lambda x: datetime.strptime(x, '%d/%m/%Y').date())
    df_recent_readings.reading_date = df_recent_readings.reading_date.apply(lambda x: datetime.strptime(x, '%d/%m/%Y').date())
    df_recent_readings.sort_values(by='reading_date', ascending=True, inplace=True)

    metrics_data_30days = data_treatement.clear_dataframe(metrics_data_30days, col_subset='name', vl_to_exclude='Homologação LAB COMGÁS')
    df_all_unit_services = data_treatement.clear_dataframe(df_all_unit_services, col_subset='Unidade de Negócio - Nome', vl_to_exclude='Homologação LAB COMGÁS')
    df_recent_readings = data_treatement.clear_dataframe(df_recent_readings, col_subset='name', vl_to_exclude='Homologação LAB COMGÁS')

    df_sla_per_city = df_all_unit_services.groupby(by='Cidade - Nome').agg({'IEF':'mean', 'Matrícula':'count'}).apply(lambda x: round(x, 2)).sort_values(by='IEF', ascending=True)
    df_sla_all_BU = df_all_unit_services.groupby('Unidade de Negócio - Nome').agg({'IEF':'mean', 'Matrícula':'count'}).reset_index()
    all_metrics_grouped_by_dt = metrics_data_30days.groupby(by='snapshot_date').mean()

    st.header('SLA: métricas')
    st.markdown('---')
    st.markdown('###')
    gauge_chart = sla_indicator_chart.gauge_sla_figure(df_sla_all_BU)
    sla_per_city_fig = sla_per_city.sla_per_city(df_sla_per_city)
    all_metrics_fig = sla_bat_rssi_all_project.metrics_all_projects(all_metrics_grouped_by_dt)
    sla_30days = sla_last_30days.sla_last_30days(metrics_data_30days)
    rssi_30days = rssi_last_30days.rssi_last_30days(metrics_data_30days)
    boxplot_metrics = metrics_boxplot.metrics_boxplot(metrics_data_30days)
    battery_voltage30days = battery_voltage_last30days.battery_voltage(metrics_data_30days)
    st.plotly_chart(gauge_chart, use_container_width=True)
    st.markdown('---')
    st.markdown('###')
    st.plotly_chart(sla_per_city_fig, use_container_width=True)
    st.markdown('---')
    st.header('Overall Analysis - Last 30 days :chart_with_upwards_trend:')
    st.markdown('---')
    st.markdown('###')
    st.plotly_chart(all_metrics_fig, use_container_width=True)
    st.markdown('---')
    st.markdown('###')
    sla_c, rssi_c, bat_c = st.columns(3)
    sla_c.plotly_chart(sla_30days, use_container_width=True)
    rssi_c.plotly_chart(rssi_30days, use_container_width=True)
    bat_c.plotly_chart(battery_voltage30days, use_container_width=True)
    st.markdown('###')
    st.markdown('###')
    st.plotly_chart(boxplot_metrics, use_container_width=True)
    st.markdown('---')
    st.header('Análise de Leituras Diárias')
    st.markdown('---')
    st.markdown('###')
    recent_readings_fig = recent_reading.recent_reading(data=df_recent_readings)
    st.plotly_chart(recent_readings_fig, use_container_width=True)
    st.markdown('---')
    st.header('Análise de Transmissões Diárias')
    st.markdown('---')
    st.markdown('###')
    daily_transmission_fig = transmissions.daily_transmissions(df_daily_transmissions)
    st.plotly_chart(daily_transmission_fig, use_container_width=True)

# geospacial analysis code
from sqlalchemy.engine import result
import streamlit as st
import datetime
from queries import querie_builder, data_treatement
from shapely import Point
from filters import Filters
from figures import sla_maps, stastics_fig, update_figs_layout
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from stqdm import stqdm
from polygons import polygons
import pandas as pd
from queries import queries_raw_code
import session_states
import googlemaps
import json
from math import trunc
    
def geo_analysis(results: querie_builder.Queries, profile_to_simulate):
    # inicialização das variáveis de sessão
    session_states.initialize_session_states([('main_data', pd.DataFrame()), ('grouped_data', pd.DataFrame()), ('general_data', pd.DataFrame())])

    #inicilização da API do Google
    gmaps = googlemaps.Client(key=st.secrets.googleapi.apikey)

    # variável de conexão temporária
    tmp_connection = querie_builder.Queries(name='temporary_queries')

    jardins_coordenadas = data_treatement.read_data('coordenadas_jardins.csv')
    
    #inicialização dos dados necessários
    if st.session_state.main_data.shape[0] == 0:
        df_all_unit_services = results['ALL_UNITS']
        df_all_unit_services['Ponto'] = list(zip(df_all_unit_services['Latitude'], df_all_unit_services['Longitude']))
        df_all_unit_services['Ponto'] = df_all_unit_services['Ponto'].apply(lambda x: Point(x))
        st.session_state.general_data = df_all_unit_services.copy()

    else:
        df_all_unit_services = results['ALL_UNITS']
        df_all_unit_services['Ponto'] = list(zip(df_all_unit_services['Latitude'], df_all_unit_services['Longitude']))
        df_all_unit_services['Ponto'] = df_all_unit_services['Ponto'].apply(lambda x: Point(x))
    

    agrupado_por_condo = df_all_unit_services.groupby(by=['Unidade de Negócio - Nome','Cidade - Nome', 'Grupo - Nome', 'Endereço']).agg({'IEF':np.mean, 'Matrícula':'count', 'Latitude':np.mean, 'Longitude':np.mean}).reset_index()
    agrupado_por_condo.IEF = agrupado_por_condo.IEF.apply(lambda x: round(x, 2))
    
    st.markdown('---')
    st.subheader('Filters')
    filtered_group = Filters(agrupado_por_condo)
    filtered_data = Filters(df_all_unit_services)
    
    # Formulários pra filtros de queries
    with st.form(key='submit_sla_form'):
        c_BU, c_city = st.columns(2)
        filtro_BU = c_BU.multiselect('Business Unit', options=filtered_data.df['Unidade de Negócio - Nome'].unique(), key='bu_filter')
        st.session_state.city_filter = c_city.multiselect('City', options=filtered_data.df['Cidade - Nome'].unique(), key='cityfilter')
        
        c_address, c_group = st.columns(2)
        st.session_state.address_filter = c_address.multiselect('Address name', options=filtered_data.df['Endereço'].unique())
        st.session_state.residence_filter = c_group.multiselect('Residence name', options=filtered_data.df['Grupo - Nome'].unique())

        c_num_min, c_num_max, c_status_date = st.columns(3)


        min_pontos = c_num_min.number_input('Min number of installations:', min_value=0, value=0)
        max_pontos = c_num_max.number_input('Max number of installations:', min_value=0, value=5000)

        status_date = c_status_date.date_input('Day of the status', value=datetime.datetime.today(), max_value=datetime.datetime.today())
        min_sla_condo, max_sla_condo = c_num_min.slider('SLA por condomínio', min_value=0.0, max_value=100.0, value=[float(filtered_group.df.IEF.min()),float(filtered_group.df.IEF.max())], step=5.0)
        min_sla_pontos, max_sla_pontos = c_num_max.slider('SLA por instalação', min_value=0.0, max_value=100.0, value=[float(filtered_data.df.IEF.min()),float(filtered_data.df.IEF.max())], step=5.0, key='sla_slider_pontos')
        submit_form = st.form_submit_button('Submit the form')
        if submit_form:
            # caso o botão seja apertado, uma query individual é disparada com os filtros
            new_query = queries_raw_code.all_units_info(status_date, bussiness_unts=filtro_BU, cities=st.session_state.city_filter, addresses=st.session_state.address_filter, residences=st.session_state.residence_filter,
                                                        company_id=profile_to_simulate)

            filtered_data.df  = pd.DataFrame(tmp_connection.run_single_query(command=new_query))
            filtered_data.general_qty_filter(min_sla_pontos, max_sla_pontos, 'IEF')

            filtered_data.validate_filter('general_filter', st.session_state.city_filter, refer_column='Cidade - Nome')

            filtered_group.df = filtered_data.df.groupby(by=['Unidade de Negócio - Nome','Cidade - Nome', 'Grupo - Nome', 'Endereço'])\
            .agg({'IEF':np.mean, 'Matrícula':'count', 'Latitude':np.mean, 'Longitude':np.mean, 'data snapshot':np.max}).reset_index()
            filtered_group.df.IEF = filtered_group.df.IEF.apply(lambda x: round(x, 2))


            # filtered_group.validate_filter('general_filter', filtro_BU, refer_column='Unidade de Negócio - Nome')
            # filtered_group.validate_filter('general_filter', st.session_state.address_filter, refer_column='Endereço')
            # filtered_group.validate_filter('general_filter', st.session_state.residence_filter, refer_column='Grupo - Nome')    

    filtered_group.df = filtered_group.df[(filtered_group.df['Matrícula'] >= min_pontos) &
                                (filtered_group.df['Matrícula'] <= max_pontos) &
                                (filtered_group.df['IEF'] >= min_sla_condo) & (filtered_group.df['IEF'] <= max_sla_condo)]
        
    # filtered_data.general_filter(refer_column='Unidade de Negócio - Nome', opcs=filtered_group.df['Unidade de Negócio - Nome'])
    # filtered_data.general_filter(refer_column='Endereço', opcs=filtered_group.df['Endereço'])
    # filtered_data.general_filter(refer_column='Grupo - Nome', opcs=filtered_group.df['Grupo - Nome'])
    # filtered_data.general_filter(refer_column='Cidade - Nome', opcs=filtered_group.df['Cidade - Nome'])

    st.session_state.main_data = filtered_data.df
    st.session_state.grouped_data = filtered_group.df
    cp_main_data = st.session_state.main_data.copy()
    
    with st.expander('Filtered data:'):
        st.session_state.grouped_data.rename(columns={'Matrícula':'Pontos instalados'}, inplace=True)
        st.write(st.session_state.grouped_data.sort_values(by='Pontos instalados', ascending=False))
        st.session_state.main_data.sort_values(by='IEF', ascending=False, inplace=True)
        st.markdown('---')
        st.data_editor(st.session_state.main_data,
                column_config={
                    "IEF":st.column_config.ProgressColumn('SLA', min_value=0, max_value=100, format='%.2f')
                })

    theme_position, ponto_filtrado, sla_filtrado, opc_agrupamento, *_ = st.columns(5)
    theme_position.metric('Filtered addresses:', f'{st.session_state.grouped_data.shape[0]} ({round(st.session_state.grouped_data.shape[0] / len(agrupado_por_condo) * 100, 2)})%',
                        help=f'Total of addresses: {len(agrupado_por_condo)}')
    ponto_filtrado.metric('Pontos filtrados:', f'{st.session_state.main_data.shape[0]} ({round(len(st.session_state.main_data) / filtered_data.df.shape[0] * 100, 2)})%',
                        help=f'Total of installations: {st.session_state.general_data.shape[0]}')
    sla_filtrado.metric('Filtered SLA %', value=f'{round(np.mean(st.session_state.main_data.IEF), 2)}%')
    st.markdown('---')
    
    st.session_state.all_points_figure = sla_maps.plot_sla_map(st.session_state.main_data, title='SLA % per installation', colmn_to_base_color='IEF', theme='streets', group_type='IEF')
    st.session_state.grouped_points_figure = sla_maps.plot_sla_map(st.session_state.grouped_data, title=f'Installations per address', theme='streets', group_type='Pontos instalados',
                                        colmn_to_base_color='Pontos instalados')
    st.session_state.grouped_sla_figure = sla_maps.plot_sla_map(st.session_state.grouped_data, title=f'SLA % mean grouped per address', theme='streets', group_type='IEF',
                                        colmn_to_base_color='IEF')

    sla_maps.add_traces_on_map(st.session_state.all_points_figure, another_data=jardins_coordenadas, name='Jardins Area', fillcolor='rgba(31, 54, 251, 0.3)')
    sla_maps.add_traces_on_map(st.session_state.grouped_points_figure, another_data=jardins_coordenadas, name='Jardins Area', fillcolor='rgba(31, 54, 251, 0.3)')
    sla_maps.add_traces_on_map(st.session_state.grouped_sla_figure, another_data=jardins_coordenadas, name='Jardins Area', fillcolor='rgba(32, 54, 251, 0.3)')
    
    try:
        metricas_sla_indiv = st.session_state.main_data.describe().drop('count', axis=0).reset_index().rename(columns={'index':'metricas'})
        metricas_sla_indiv.IEF = metricas_sla_indiv.IEF.apply(lambda x: round(x, 2))
        metricas_sla_indiv.metricas = ['SLA % mean', 'Standard deviation', 'Minimum SLA %', '25% of the data', '50% of the data', '75% of the data', 'Maximum SLA %']
        fig_descritiva = stastics_fig.analise_descritiva(metricas_sla_indiv)
        st.plotly_chart(fig_descritiva, use_container_width=True)
        qty_that_is_contained = 0
        st.markdown('---')
    except:
        pass


    st.subheader('Gateways analysis')
    with st.expander('Edit gateway options'):
        with st.form('gtw_form', clear_on_submit=False):
            c_gtw_number, c_gtw_range = st.columns(2)
            #qty_of_gtw = c_gtw_number.number_input('Distribute some gateways: ', min_value=0, max_value=st.session_state.grouped_data['Pontos instalados'].max())
            st.session_state.extra_selected_address = c_gtw_number.multiselect('Or choose any address', options=st.session_state.general_data['Endereço'].unique(), key='address')
            st.session_state.extra_selected_residence = c_gtw_range.multiselect('Or choose any residence name', options=st.session_state.general_data['Grupo - Nome'].unique(), key='residence')

            personalized_gtw = st.session_state.general_data[(st.session_state.general_data['Endereço'].isin(st.session_state.extra_selected_address)) | 
                                                             (st.session_state.general_data['Grupo - Nome'].isin(st.session_state.extra_selected_residence))]

            gtw_range = c_gtw_range.number_input('Gateway range in meters: ', min_value=1, value=1000)

            grouped_personalized = personalized_gtw.groupby(by=['Unidade de Negócio - Nome','Cidade - Nome', 'Grupo - Nome', 'Endereço']).agg({'IEF':np.mean, 'Matrícula':'count', 'Latitude':np.mean, 'Longitude':np.mean}).reset_index()
            #df_filtered_per_points = st.session_state.grouped_data.sort_values(by='Pontos instalados', ascending=False).iloc[:int(qty_of_gtw), :].reset_index()
            #df_filtered_per_points = pd.concat([df_filtered_per_points, personalized_gtw.reset_index()], ignore_index=True)
            grouped_personalized.sort_values(by='Matrícula', ascending=False, ignore_index=True, inplace=True)
            grouped_personalized.drop_duplicates(subset=['Endereço'], inplace=True, ignore_index=True, keep='first')
            grouped_personalized.drop_duplicates(subset=['Grupo - Nome'], inplace=True, ignore_index=True, keep='first')
            submit_gtw = st.form_submit_button('Start calculations')
            st.subheader('Ordem de prioridade para instalação de gateways')
            st.write(grouped_personalized)
            if submit_gtw: st.session_state.gtw_filters = True
                            
    if st.session_state.gtw_filters:
        st.session_state.gtw_filters = False
        lat_list, lon_list = grouped_personalized['Latitude'].to_numpy(), grouped_personalized['Longitude'].to_numpy()
        with st.spinner('Calculate polygons...'):
            with ThreadPoolExecutor(4) as executor:
                list_of_polygons = list(executor.map(polygons.calculate_polygons, lat_list, lon_list, [gtw_range]*len(lat_list)))
        
        contained_index = []
        with st.spinner('Calculating polygons...'):
            with ThreadPoolExecutor(4) as executor:
                for n in stqdm(range(len(lat_list))):
                    current_polygon, current_list_of_circles = list_of_polygons[n][0], list_of_polygons[n][1]
                    args = [(index, row[-1], current_polygon) for index, *row in cp_main_data.itertuples()]
                    results = executor.map(polygons.check_if_pol_contains, args)
                    contained_index.extend([i for i in results if i is not None])
                    cp_main_data = cp_main_data[~cp_main_data.index.isin(contained_index)]

                    temporary_lats = [tuple_of_coords[0] for tuple_of_coords in current_list_of_circles]
                    temporary_longs = [tuple_of_coords[1] for tuple_of_coords in current_list_of_circles]

                    st.session_state.polygon_df = polygons.tmp_coordinates(temporary_lats, temporary_longs)
                    if st.session_state.polygon_df is not None:
                        sla_maps.add_traces_on_map(st.session_state.grouped_points_figure, another_data=st.session_state.polygon_df, fillcolor='rgba(20, 2222, 169, 0.4)', name=grouped_personalized.loc[n:n, 'Endereço'].values[0])
                        sla_maps.add_traces_on_map(st.session_state.grouped_sla_figure, another_data=st.session_state.polygon_df, fillcolor='rgba(20, 222, 169, 0.4)', name=grouped_personalized.loc[n:n, 'Endereço'].values[0])                 
                        sla_maps.add_traces_on_map(st.session_state.all_points_figure, another_data=st.session_state.polygon_df, fillcolor='rgba(20, 222, 169, 0.4)', name=grouped_personalized.loc[n:n, 'Endereço'].values[0])
        
        affected_points = st.session_state.main_data.loc[contained_index]
        affected_points.drop_duplicates(subset=['Matrícula'], inplace=True)
        qty_that_is_contained = affected_points.shape[0]
        points_metrics, choosed_gtw_qtd, sla_metrics, sla_prevision, communicating = st.columns(5)
        
        if grouped_personalized.shape[0] >= 1:
            mean_sla_affecteds = round(affected_points['IEF'].mean(), 2)
            points_metrics.metric(f'Affected points', value=f'{qty_that_is_contained} pontos')
            choosed_gtw_qtd.metric('Quantity of gateways: ', value=f'{len(lat_list)} gateways')
            sla_metrics.metric(f'Filtered SLA %', value=mean_sla_affecteds)

            improvement_preview = round(trunc(qty_that_is_contained - ((mean_sla_affecteds/100) * qty_that_is_contained)) / st.session_state.main_data.shape[0] * 100, 2)
            sla_prevision.metric('Improvement preview over the general SLA %', value=f'{improvement_preview}%', help=f"Considering {st.session_state.main_data.shape[0]} points")

            with st.expander('Addresses and installations affected'):
                st.write(affected_points)
                st.write(st.session_state.grouped_data[st.session_state.grouped_data['Endereço'].isin(affected_points['Endereço'].unique())].sort_values(by='Pontos instalados', ascending=False))
    
    with st.form(key='change_location'):
        go_to_location = st.text_input('Type a location to go')
        confirm_location = st.form_submit_button('Change location')
        if confirm_location:
            geocode_result = gmaps.geocode(go_to_location)
            converted_to_json = json.dumps(geocode_result)
            location = geocode_result[0]['geometry']['location']
            lat, lon = location['lat'], location['lng']
            st.session_state.all_points_figure.update_mapboxes(center=dict(lat=lat, lon=lon), zoom=16)
            st.session_state.grouped_sla_figure.update_mapboxes(center=dict(lat=lat, lon=lon), zoom=16)
            st.session_state.grouped_points_figure.update_mapboxes(center=dict(lat=lat, lon=lon), zoom=16)
    
    theme_position, *_ = st.columns(5)
    theme_options = ['satellite-streets', 'open-street-map', 'satellite', 'streets', 'carto-positron', 'carto-darkmatter', 'dark', 'stamen-terrain', 'stamen-toner',
                        'stamen-watercolor', 'basic', 'outdoors', 'light', 'white-bg']
    choosed_theme = theme_position.selectbox('Choose any theme', options=theme_options, index=0)
    update_figs_layout.update_fig_layouts([st.session_state.grouped_points_figure, st.session_state.grouped_sla_figure, st.session_state.all_points_figure], theme=choosed_theme)


    tab_grouped_condo, tab_grouped_sla, tab_all_points = st.tabs(['SLA map grouped by address', 'SLA map grouped by average SLA', 'SLA map - All points'])
    with tab_grouped_condo:
        st.plotly_chart(st.session_state.grouped_points_figure, use_container_width=True)
    with tab_grouped_sla:
        st.plotly_chart(st.session_state.grouped_sla_figure, use_container_width=True)
    with tab_all_points:
        st.plotly_chart(st.session_state.all_points_figure, use_container_width=True)



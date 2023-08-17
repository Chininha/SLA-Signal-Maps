import streamlit as st
from queries.all_queries import queries_constants
import session_states
from typing import Union, Dict
from queries import querie_builder
from views import main_sidebar
import importlib
from queries import queries_raw_code

class App:


    def __init__(self, name) -> None:
        self.app_name = name

    def apply_styles(self, style_file:str) -> None:
        with open(style_file) as style:
            st.markdown(f'<style>{style.read()}</style>', unsafe_allow_html=True)

    def start_app(self, app_session_state) -> None:
        if app_session_state != 'Error on connect to the database' and st.session_state.ALL_RESULTS != {}:
                
                choosed_app = main_sidebar.main_sidebar()
                choosed_module = importlib.import_module(choosed_app)
                module_name = choosed_module.__name__
                function_name = main_sidebar.module_mapping[module_name]
                choosed_function = getattr(choosed_module, function_name)
                choosed_function(results=st.session_state.ALL_RESULTS)
    
    def build_app(self) -> Union[Dict, str]:
        session_states.initialize_session_states([('start_querie', False),('ALL_RESULTS', {}), ('clear_cache', False)])
        queries_instancy = querie_builder.Queries(name='laager_queries')
        connection_state = queries_instancy.verify_connection()

        if connection_state == 'success':
            st.success('Connection succeded!')
            queries_instancy.add_queries(queries_constants)
            c_start_querie, c_clear_cache, _, stop_queries, *_ = st.columns(10, gap='small')
            start_querie = c_start_querie.button('Sync database', key='start_queries', type='primary')
            clear_cache = c_clear_cache.button('Clear caches', key='clearcache', type='primary')
            if clear_cache:
                st.cache_data.clear()
                st.session_state.clear_cache = False

            if start_querie:
                st.session_state.start_querie = False
                stop_querie_flag = stop_queries.button('Stop queries', type='secondary')
                if not stop_querie_flag:
                    with st.spinner('Running queries.'):
                        cities = queries_instancy.run_single_query(command='SELECT name FROM cities WHERE company_id = 38;')
                        main_df = queries_instancy.run_single_query(command=queries_raw_code.all_units_info(cities=cities['name'].to_list()))
                        
                        st.session_state.ALL_RESULTS = queries_instancy.run_queries(queries_instancy.all_queries_commands)
                        st.session_state.ALL_RESULTS['ALL_UNITS'] = main_df
                    stop_querie_flag = st.empty()

            return st.session_state.ALL_RESULTS
        return 'Error on connect to the database'
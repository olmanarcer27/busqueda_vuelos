# Aplicación en Streamlit
st.title("Chatbot de Búsqueda de Vuelos ✈️")
ciudad_origen = st.text_input("Ingrese la ciudad de origen:")
ciudad_destino = st.text_input("Ingrese la ciudad de destino:")
fecha = st.date_input("Seleccione la fecha de salida:").strftime("%Y-%m-%d")
adultos = st.number_input("Cantidad de pasajeros:", min_value=1, step=1)

if st.button("Buscar vuelos"):
    origen = obtener_codigo_iata(ciudad_origen)
    destino = obtener_codigo_iata(ciudad_destino)
    
    if not origen:
        st.error(f"No se encontró un código IATA para la ciudad de origen: {ciudad_origen}")
    if not destino:
        st.error(f"No se encontró un código IATA para la ciudad de destino: {ciudad_destino}")
    
    if origen and destino:
        vuelos = buscar_vuelos(origen, destino, fecha, adultos)
        if vuelos:
            for vuelo in vuelos:
                st.write(vuelo)
        else:
            st.warning("No se encontraron vuelos para la búsqueda realizada.")

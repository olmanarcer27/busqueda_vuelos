import streamlit as st
import os
from amadeus import Client, ResponseError
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import string
import time

# URL del XML con las tasas de cambio del ECB
url = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'

# Obtener el contenido del XML desde el ECB
response = requests.get(url)

# Verificar si la solicitud fue exitosa
if response.status_code == 200:
    # Parsear el XML con BeautifulSoup
    soup = BeautifulSoup(response.content, 'xml')
    
    # Buscar el elemento que contiene la tasa de EUR/USD
    usd_cube = soup.find('Cube', {'currency': 'USD'})
    tasa_eurusd = usd_cube['rate']
else:
    print(f"Error al obtener los datos: {response.status_code}")

# Cargar credenciales de Amadeus desde variables de entorno
load_dotenv()
amadeus = Client(
    client_id=os.getenv("AMADEUS_CLIENT_ID"),
    client_secret=os.getenv("AMADEUS_CLIENT_SECRET")
)

def obtener_codigo_iata(ciudad):
    """Obtiene el código IATA de una ciudad o aeropuerto."""
    try:
        response = amadeus.reference_data.locations.get(keyword=ciudad, subType="CITY,AIRPORT")
        if response.data:
            return response.data[0].get("iataCode")
    except ResponseError as error:
        st.error(f"Error al obtener código IATA: {error}")
    return None


def obtener_lista_ciudades_aeropuertos():
    """Obtiene una lista de todas las ciudades y aeropuertos disponibles en Amadeus utilizando varias consultas con letras del abecedario."""
    ciudades_aeropuertos = []
    
    # Hacemos solicitudes para cada letra del abecedario
    for letra in string.ascii_uppercase:
        try:
            response = amadeus.reference_data.locations.get(keyword=letra, subType="CITY,AIRPORT")
            if response.data:
                ciudades_aeropuertos.extend([ciudad['name'] for ciudad in response.data])
        except ResponseError as error:
            # Ignorar los errores 429 y otros, sin mostrar al usuario
            if error.status_code != 429:
                st.error(f"Error al obtener lista de ciudades y aeropuertos con la letra {letra}: {error}")
        
        # Pausar para evitar alcanzar el límite de solicitudes
        time.sleep(1)  # Pausa de 1 segundo
    
    # Eliminar duplicados y ordenar alfabéticamente
    return sorted(list(set(ciudades_aeropuertos)))  # Eliminar duplicados con set() y ordenar

def convertir_moneda(monto, moneda_origen, moneda_destino):
    """Convierte el monto de una moneda a otra usando la API de cambio de divisas."""
    # Si la moneda de origen y destino son iguales, no es necesario realizar la conversión
    if moneda_origen == moneda_destino:
        return monto
    else:
        return round(float(monto) * float(tasa_eurusd), 2)


def buscar_vuelos(origen, destino, fecha, adultos):
    """Busca vuelos entre dos ciudades."""
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origen,
            destinationLocationCode=destino,
            departureDate=fecha,
            adults=adultos
        )
        
        vuelos = response.data if response.data else []
        
        resultados = []
        for vuelo in vuelos:
            itinerario = vuelo.get("itineraries", [])[0].get("segments", [])
            if not itinerario:
                continue
            
            escalas = len(itinerario) - 1
            precio = float(vuelo["price"]["total"])
            moneda = vuelo["price"]["currency"]
            
            # Convertir los precios a EUR y USD si es necesario
            precio_eur = convertir_moneda(precio, moneda, "EUR")
            precio_usd = convertir_moneda(precio, moneda, "USD")
            
            detalles_vuelo = {
                "Precio Original": f"{precio} {moneda}",
                "Precio en EUR": f"{precio_eur} EUR" if precio_eur else "No disponible",
                "Precio en USD": f"{precio_usd} USD" if precio_usd else "No disponible",
                "Origen": itinerario[0]["departure"]["iataCode"],
                "Destino": itinerario[-1]["arrival"]["iataCode"],
                "Hora Salida": itinerario[0]["departure"]["at"],
                "Hora Llegada": itinerario[-1]["arrival"]["at"],
                "Escalas": escalas,
                "Aerolínea": itinerario[0]["carrierCode"],
                "Categoría": vuelo["travelerPricings"][0]["fareDetailsBySegment"][0]["cabin"],
            }
            resultados.append(detalles_vuelo)
        
        return resultados
    except ResponseError as error:
        st.error(f"Error al buscar vuelos: {error}")
        return []

# Aplicación en Streamlit
st.title("✈️ Buscador de Vuelos Inteligente")

# Guardar lista de ciudades y aeropuertos en sesión para evitar múltiples solicitudes
if "ciudades_aeropuertos_disponibles" not in st.session_state:
    st.session_state.ciudades_aeropuertos_disponibles = obtener_lista_ciudades_aeropuertos()

# Ciudad de Origen y Destino (selección desde lista estática)
origen = st.selectbox("Seleccione Ciudad de Origen:", options=st.session_state.ciudades_aeropuertos_disponibles)
destino = st.selectbox("Seleccione Ciudad de Destino:", options=st.session_state.ciudades_aeropuertos_disponibles)

fecha = st.date_input("Fecha de Salida:").strftime("%Y-%m-%d")
adultos = st.number_input("Cantidad de Pasajeros:", min_value=1, step=1)

# Establecemos el estado de la página actual
if "pagina_actual" not in st.session_state:
    st.session_state.pagina_actual = 0

if "vuelos_totales" not in st.session_state:
    st.session_state.vuelos_totales = []

if st.button("🔍 Buscar Vuelos"):
    origen_codigo = obtener_codigo_iata(origen)
    destino_codigo = obtener_codigo_iata(destino)
    
    if not origen_codigo or not destino_codigo:
        st.error("No se pudo obtener los códigos IATA. Verifique los nombres de las ciudades.")
    else:
        # Buscar todos los vuelos
        vuelos = buscar_vuelos(origen_codigo, destino_codigo, fecha, adultos)
        st.session_state.vuelos_totales = vuelos
        st.session_state.pagina_actual = 0  # Restablecer a la primera página
        if vuelos:
            st.session_state.vuelos_pagina = vuelos[:10]  # Guardar los primeros 10 vuelos en la sesión
        else:
            st.warning("No se encontraron vuelos para la búsqueda realizada.")

# Paginación de los resultados
if len(st.session_state.vuelos_totales) > 10:
    if st.session_state.pagina_actual > 0:
        if st.button("Página Anterior"):
            st.session_state.pagina_actual -= 1

    if (st.session_state.pagina_actual + 1) * 10 < len(st.session_state.vuelos_totales):
        if st.button("Página Siguiente"):
            st.session_state.pagina_actual += 1

    # Mostrar los vuelos correspondientes a la página actual
    vuelos_pagina = st.session_state.vuelos_totales[st.session_state.pagina_actual * 10 : (st.session_state.pagina_actual + 1) * 10]
    st.session_state.vuelos_pagina = vuelos_pagina  # Guardar la página actual en la sesión
    st.table(vuelos_pagina)

    st.write(f"Página {st.session_state.pagina_actual + 1}")
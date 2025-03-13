import streamlit as st
from amadeus import Client, ResponseError
import requests

# Configurar credenciales de Amadeus
amadeus = Client(
    client_id="LGnvaKKSXMxVvEpVKAGXsJkB9uljfgFb",
    client_secret="94dBn057Hs0ArIcW"
)

def convertir_moneda(monto, moneda_origen, moneda_destino):
    """Convierte el monto de una moneda a otra usando la API de Exchange Rates."""
    url = f"https://api.exchangerate-api.com/v4/latest/{moneda_origen}"
    try:
        response = requests.get(url).json()
        tasa_cambio = response.get("rates", {}).get(moneda_destino, 1)
        return round(float(monto) * tasa_cambio, 2)
    except Exception as e:
        st.error(f"Error al convertir moneda: {e}")
        return monto  # Retorna el monto original en caso de error

def obtener_codigo_iata(ciudad):
    """Convierte el nombre de una ciudad en su código IATA, buscando tanto ciudades como aeropuertos."""
    try:
        response = amadeus.reference_data.locations.get(keyword=ciudad, subType="CITY,AIRPORT")
        if response.data:
            return response.data[0].get("iataCode")
        else:
            return None
    except ResponseError as error:
        st.error(f"Error al obtener código IATA: {error}")
        return None

def buscar_vuelos(origen, destino, fecha, adultos):
    """Busca vuelos entre dos ciudades en una fecha específica con una cantidad de pasajeros editable."""
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
            precio_eur = convertir_moneda(precio, moneda, "EUR")
            precio_usd = convertir_moneda(precio, moneda, "USD")
            
            detalles_vuelo = {
                "precio_original": f"{precio} {moneda}",
                "precio_eur": f"{precio_eur} EUR",
                "precio_usd": f"{precio_usd} USD",
                "origen": itinerario[0]["departure"]["iataCode"],
                "destino": itinerario[-1]["arrival"]["iataCode"],
                "hora_salida": itinerario[0]["departure"]["at"],
                "hora_llegada": itinerario[-1]["arrival"]["at"],
                "escalas": escalas,
                "aerolinea": itinerario[0]["carrierCode"],
                "categoria": vuelo["travelerPricings"][0]["fareDetailsBySegment"][0]["cabin"],
            }
            resultados.append(detalles_vuelo)
        
        return resultados
    except ResponseError as error:
        st.error(f"Error al buscar vuelos: {error}")
        return []

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


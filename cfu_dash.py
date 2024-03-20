import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from streamlit_extras.app_logo import add_logo
import numpy as np
import re
import folium
#from folium import plugins
from folium.plugins import MarkerCluster
import altair as alt
import ast
import json
from geojson import Point, LineString, GeometryCollection, Feature, FeatureCollection

app_title = 'Coin Finds of Ukraine'
app_subtitle = 'Coin Finds of Ukraine (CFU) tracks archaic, classical, and hellenistic hoards and single-finds (600-1 BCE) on the territory of modern Ukraine'

# Map visualization
def display_map(findsg, groups, denom, date_min, date_max, material, material_dict, mint, number_min, number_max):

    # Filter the groups according to search criteria
    if denom:
        denom_dict = dictionarize(groups,'denom1')
        denom_dedict = dedictionarize(denom_dict)
        denom_changed = [denom_dedict[x] for x in denom]
        groups = groups[groups['denom1'].isin(denom_changed)]

    if material:
        material_dedict = dedictionarize(material_dict)
        material_changed = [material_dedict[x] for x in material]
        groups = groups[groups['Material 1 URI'].isin(material_changed)]

    if mint:
        mint_dict = dictionarize(groups, 'Mint 1 URI')
        mint_dedict = dedictionarize(mint_dict)
        mint_changed = [mint_dedict[x] for x in mint]
        groups = groups[groups['Mint 1 URI'].isin(mint_changed)]

    if date_min or date_max:
        groups = groups[groups['from_date'] > date_min]
        groups = groups[groups['to_date'] < date_max]

    if number_min or number_max:
        groups = groups[groups['count'] > number_min]
        groups = groups[groups['count'] < number_max]

    # Then filter finds according to the groups that are left after filtering groups
    findsg = findsg[findsg['id'].isin(list(groups['id']))]

    # Construct map starting here
    latitude = 50
    longitude = 32

    cfu_map = folium.Map(
        location=[latitude, longitude], 
        zoom_start=5, 
        tiles=None)
    # Add several basemap layers onto the blank space prepared above
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
                     name='Esri.WorldGrayCanvas',
                     attr='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ').add_to(cfu_map)

    ids = list(findsg['id'])
    latitudes = list(findsg['lat'])
    longitudes = list(findsg['long'])
    places = list(findsg['place'])

    style = lambda x: {
        'color' : 'black',
        'opacity' : '1',
        'weight' : '0.3',
        'radius' : '6',
        'fill' : 'True',
        'fillOpacity' : '0.6',
        'fillColor' : 'white'
            }
    highlight = lambda x: {
        'color' : 'white',
        'opacity' : '0.80',
        'weight' : '5',
        'fill' : 'True',
        'fillOpacity' : '0.3',
        'fillColor' : 'white'
            }

    # The spiderfy option is needed for 2-clusters, which do not separate enough to allow for a click from the user
    marker_cluster = MarkerCluster(name='mc', options={'spiderfyDistanceMultiplier':3}).add_to(cfu_map)


    for iden, latitude, longitude, place in zip(ids, latitudes, longitudes, places):

        findgroups = groups[groups['id'] == iden]
        denoms = list(findgroups['denom1'])
        denom_dict = {'nan':'Unknown'}
        mints = list(findgroups['Mint 1 URI'])
        numbers = list(findgroups['count'])
        mindates = list(findgroups['from_date'])
        maxdates = list(findgroups['to_date'])
        grouptext = ''
        totalcount = 0

        for (denom, mint, number, mindate, maxdate) in zip(denoms, mints, numbers, mindates, maxdates):
            # Weed out the nans when converting to an actual name
            try:
                denom = denom_dict[denom]
            except:
                denom = denom
            # The following just transform the formats on the sheet to something friendly for the popup
            denom = re.sub('(https://nomisma.org/id/)(.*)', '<a href="\\1\\2">\\2</a>', denom)
            mint = re.sub('(https://nomisma.org/id/)(.*)', '<a href="\\1\\2">\\2</a>', mint)
            daterange = str(mindate).replace('-','') + '-' + str(maxdate).replace('-','')
            gtemplate = f"""
            {denom} ({mint}, {daterange} BCE): {number}<br>"""
            grouptext = grouptext + gtemplate
            try:
                totalcount = totalcount + int(number)
            except:
                totalcount = totalcount
        iden = iden.replace('cfu', '')

        if totalcount == 1:
            werewas = 'coin was'
        else:
            werewas = 'coins were'

        label = f"""
<h3> CFU Coin Find {iden}</h3><br>
This coin find was found in {place}. In total, {totalcount} {werewas} found.
  <p>
{grouptext}
  </p>
        """
        html = folium.Html(label, script=True)

        folium.features.CircleMarker(
        [latitude, longitude],
        radius=6,
        color='black',
        fill='True',
        fill_color='white',
        fill_opacity=0.6,
        weight=0.3,
        popup=folium.Popup(html, parse_html=True, max_width=500)).add_to(marker_cluster)


    return cfu_map, groups


# Main app
def main():
    dates = pd.read_excel('Coin Finds of Ukraine (CFU) - Master Sheet.xlsx', sheet_name='Deposit Dates')
    dispo = pd.read_excel('Coin Finds of Ukraine (CFU) - Master Sheet.xlsx', sheet_name='Disposition, Refs, and Notes')
    places = pd.read_excel('Coin Finds of Ukraine (CFU) - Master Sheet.xlsx', sheet_name='Findspots')
    groups = pd.read_excel('Coin Finds of Ukraine (CFU) - Master Sheet.xlsx', sheet_name='Hoard Contents')
    finds = pd.read_excel('Coin Finds of Ukraine (CFU) - Master Sheet.xlsx', sheet_name='Hoard Total Count')

    places = places.rename(columns={"IGCH lat": "lat", "IGCH long": "long"})
    finds = finds.rename(columns={"total count": "number"})
    groups = groups.rename(columns={"Unnamed: 0": "id", "Denomination 1 URI": "denom1"})

    st.set_page_config('Coin Finds of Ukraine', page_icon='browsericon.png', layout='wide')

    # Create basic visual elements
    st.title(app_title)
    st.caption(app_subtitle)
    st.markdown("""
            <style>
                .block-container {
                        padding-top: 1.5rem;
                        padding-bottom: 0rem;
                        padding-left: 1rem;
                        padding-right: 1rem;
                    }
                [data-testid=stSidebar] {
                    padding-left: 0rem;
                    }
            </style>
            """, unsafe_allow_html=True)

    findsg = finds.join(dates.set_index('id'), on='id', how='left', lsuffix='_left', rsuffix='_right')
    findsg = findsg.join(places.set_index('id'), on='id', how='left', lsuffix='_left', rsuffix='_right')
    findsg = findsg.dropna(subset=['lat', 'long'])

    groups = groups.dropna(subset=['from_date', 'to_date'])
    groups.fillna('Unknown', inplace=True)
    groups = groups.replace({'count':{'?':0, 'Unknown':0}})

    dates = dates.dropna(subset=['from','to','fromDate','toDate'])

    global dictionarize
    def dictionarize(df, col):
        dict_candidates = list(df[col].unique())
        dict_final = {}
        for i in dict_candidates:
            y = re.sub('(http)(.*)(://nomisma.org/id/)(.*)', '\\4', i)
            y = y.capitalize()
            dict_final.update({i:y})
        return dict_final
        #st.write(dict_final)

    global dedictionarize
    def dedictionarize(dictionary):
        dedictionary = {v: k for k, v in dictionary.items()}
        return dedictionary

#    def searchbar_maker(df, col, title):
#        list_name = list(df[col].unique())
#        list_name = [x for x in list_name if str(x) != 'nan']
#        list_name.sort()
#        selector = st.sidebar.multiselect(title, (list_name))
#        return selector

    def searchbar_maker(df, col, title):
        dictionary = dictionarize(df, col)
        list_name = list(df[col].unique())
        list_name = [x for x in list_name if str(x) != 'nan']
        list_name_changed = [dictionary[x] for x in list_name]
        list_name_changed.sort()
        selector = st.sidebar.multiselect(title, (list_name_changed))
        return selector


    # The local version above doesn't work with the online one. Below is online.
    with st.sidebar:
        st.image("logo.png", width=None)
        # Below is a bit of a hack. no built-in method of changing sidebar margin.
        # Instead, a css element is directly set using st.markdown.
        # the .css-ysnqb2.egzxvld4 bit must be changed depending on the app.
        # Use inspect element to see what this might be
        st.markdown("""
    <style>
        .css-ysnqb2.ea3mdgi4 {
        margin-top: -75px;
        }
    </style>
    """, unsafe_allow_html=True)


    # Http URLs make their way in. Need to replace that here to avoid problems down the road (duplications etc.)
    groups = groups.replace({'http:': 'https:'}, regex=True)


    # The Nomisma URI's are unhelpful to us on metal names, as they use periodic table symbols. So we need a further dictionary...
    material_dict = {'https://nomisma.org/id/ae':'Bronze', 'https://nomisma.org/id/ar':'Silver', 'https://nomisma.org/id/av':'Gold', 'https://nomisma.org/id/cu':'Copper','https://nomisma.org/id/el':'Electrum','Unknown':'Unknown', 'https://nomisma.org/id/an_or_av_issuer_rrc':'Silver (AN or AV, Republican Moneyer)'}
    material_name = list(groups['Material 1 URI'].unique())
    material_name = [x for x in material_name if str(x) != 'nan']
    material_name_changed = [material_dict[x] for x in material_name]
    material_name_changed.sort()
    material = st.sidebar.multiselect('Search by Material', (material_name_changed))
    # Make the searchbars
    denom = searchbar_maker(groups, 'denom1', "Search Denomination")
    mint = searchbar_maker(groups, 'Mint 1 URI', "Search by Mint")

    slider_min = min(list(findsg['fromDate_left']))
    slider_max = max(list(findsg['toDate_left']))
    date_slider = st.sidebar.slider('Date Range of Coins', slider_min, slider_max, (slider_min,slider_max))
    date_min = date_slider[0]
    date_max = date_slider[1]


    slider_min = min(list(groups['count']))
    slider_max = max(list(groups['count']))
    number_slider = st.sidebar.slider('Number of Coins in Hoard', slider_min, slider_max, (slider_min,slider_max))
    number_min = number_slider[0]
    number_max = number_slider[1]

    cfu_map, groups = display_map(findsg, groups, denom, date_min, date_max, material, material_dict, mint, number_min, number_max)
    folium.LayerControl().add_to(cfu_map)
    st.data = st_folium(cfu_map, width=None, height=600)
    #c1, c2 = st.columns(2)
    #with c1:
    #    output = st_folium(cfu_map, width=None, height=600)
    #with c2:
    #    st.write(output)

    #st.write(dates)
    #st.write(dispo)
    #st.write(places)
    #st.write(groups)
    #st.write(findsg)
    #st.write(groups)

if __name__ == '__main__':
    main()

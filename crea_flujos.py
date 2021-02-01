
# crea_flujos.py
# This file is part of CO2Dash
# Copyright (c) 2021 Jorge Tornero @imasdemase

# Foobar is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Foobar is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <https://www.gnu.org/licenses/>.

#!/usr/bin/env python3

import json
from configobj import ConfigObj


    
# Leemos el fichero de configuración de sensores, etc. Usaremos configobj en lugar
# del más sencillo configparser porque facilita mucho el trabajo con diferentes
# salas al permitir subsecciones
# TODO: Realizar chequeos básicos del fichero de configuración y cargarlo a partir de sys.argv

try:
    conf = ConfigObj('sensor.conf')
        
except Exception as e:
        print (e)


# Cargamos el fichero JSON que sireve como plantilla para crear los diferentes elementos 
# del JSON que se importará en node-reduce
# Tomaremos los diferentes nodos de la plantilla, los modificaremos y los meteremos en un
# nuevo JSON
# Al ser un árbol de nodos, los id identifican los nodos que, dependiendo del nodo,
# identificarán a los superiores en la jerarquía del flujo. Estos los guardaremos para reutilizarlos. 
# Así, por ejemplo, el ID del BROKER MQTT se utiliza posteriormente en todos los nodos MQTT IN,
# el ID del TAB se referencia desde las funciones...

# TODO: usar WITH con el archivo, etc. y poder cargarlo a partir de sys.argv

jsonPlantilla = json.load(open('./json_flujo.json'))

# Creamos una lista que almacenará cada una de las partes del JSON final

jsonFinal = []

# 1. Extraemos la configuracion de sitio aprovechando para 
# crear el JSON que utilizaremos posteriormente como salida
# y lo configuraremos apropiadamente.

sitio = jsonPlantilla["SITIO"]
sitio['id'] = conf['SITIO']['id']
sitio['site']['name'] = conf['SITIO']['name']
jsonFinal.append(sitio)

# 2. Ahora configuramos el TAB de node-red

tabNode = jsonPlantilla["TAB"]
tabNode_ID = conf['APP']['id']
tabNode['id'] = tabNode_ID
tabNode['label'] = conf['APP']['label']

jsonFinal.append(tabNode)

# 3. Configuramos el broker MQTT

broker= jsonPlantilla['BROKER']
broker_ID = conf['BROKER']['id']
broker['id'] = broker_ID
broker['broker'] = conf['BROKER']['broker_ip']
broker['name'] = conf['BROKER']['name']
broker['port'] = conf['BROKER']['port']

jsonFinal.append(broker)

# 4. Configuramos el TAB del DASHBOARD

tabUI = jsonPlantilla['TABUI']
tabUI_ID = conf['TAB']['id']
tabUI['id'] = tabUI_ID

jsonFinal.append(tabUI)

# 5. Ahora configuraríamos el dialogo que alerta si uno de los sensores 
# está por encima de los niveles
# TODO

# 6. Ahora viene la parte de configurar todos los sensores, que se pueden asociar
# a una sala, habitación, aula... dado que en el dashboard de nod-red se agrupan bajo
# ui_groups, iteraremos sobre als secciones del fichero de configuracion apropiadas.
# También rercuperamos los valores umbral para las alarmas en ppm de CO2
# Cada una de las salas está formada por un ui_group (que depende de un TABUI), un cliente mqtt, una función
# que procesa el mensaje mqtt y un dial que muestra la concentración de CO2 y un gráfico 
# que muestra el histórico
# TODO: un dial que muestre la tendencia de la concentración de CO2 en los últimos X minutos

nivel_aviso = conf['SENSORES']['nivel_aviso']
nivel_peligro = conf['SENSORES']['nivel_peligro']

# Cada una de las subsecciones del fichero de configuración representa una sala. El JSON

salas=conf['SENSORES'].sections

# Esto nos servirá para posicionar los elementos en el panel de control node-red
sala_x=150
sala_y=75

for sala in salas:
    
    # Primero creamos el ui_group correspondiente a cada
    # sala, a partir de la plantilla. El campo z de uiGroup referencia
    # jerárquicamente al la TAB mediante tabUI_ID
    uiGroup = jsonPlantilla['UIGROUP'].copy()
    uiGroup_ID = conf['SENSORES'][sala]['id']
    uiGroup['id'] = uiGroup_ID
    uiGroup['tab'] = tabUI_ID
    uiGroup['order']=salas.index(sala)+1 # Valor 0 envía el grupo UI al final
    uiGroup['name'] = conf['SENSORES'][sala]['name']
    
    
    # Ahora añadimos el cliente MQTT
    
    mqttClient = jsonPlantilla['MQTTIN'].copy()
    mqttClient_ID = conf['SENSORES'][sala]['id'] + '_mqtt' # Para identificar correctamente
    mqttClient['id'] = mqttClient_ID
    mqttClient['z'] = tabUI_ID
    mqttClient['broker'] = broker_ID
    mqttClient['topic'] = conf['SENSORES'][sala]['topic_mqtt']
    mqttClient['name'] = conf['SENSORES'][sala]['name']
    
    mqttClient['x'] = sala_x
    mqttClient['y'] = sala_y
    
    # La función que convierte el mensaje en valores de PPM CO2
    # y también pasa a la template el color de fondo de cada grupo
    # para indicar las alertas
    
    funcion="""a=msg.payload[3]
                b=msg.payload[4]
                res=a*256+b
                if (res<=%s)
                    col='#60A917'
                else if (res>%s && res<=%s)
                    col='#E3C800'
                else if(res>%s)
                    col='#E51400'
                var newMsg = { payload: res, colorAlerta: col };
                return newMsg;""" %(nivel_aviso,nivel_aviso,nivel_peligro,nivel_peligro)
    
    function = jsonPlantilla['FUNCTION'].copy()
    function_ID = conf['SENSORES'][sala]['id'] + '_funcion'
    function['id'] = function_ID
    function['z'] = tabUI_ID
    function['func'] = funcion
    function['name'] = 'DATOS -> PPM (' + conf['SENSORES'][sala]['name'] + ')'
    
    function['x'] = sala_x + 250
    function['y'] = sala_y
    
    # El dial conconcentracion CO2
    
    dial = jsonPlantilla['GAUGE'].copy()
    dial_ID = conf['SENSORES'][sala]['id'] + '_dial'
    dial['id'] = dial_ID
    dial['group'] = uiGroup_ID
    dial['name'] = 'DIAL (' + conf['SENSORES'][sala]['name'] + ')'
    dial['title'] = '[CO<sub>2</sub>]'
    dial['label'] = 'ppm'
    dial['seg1'] = nivel_aviso
    dial['seg2'] = nivel_peligro
    
    dial['x'] = sala_x+750
    dial['y'] = sala_y-50
    
    # El histórico de concentración de CO2
    
    grafico = jsonPlantilla['CHART'].copy()
    grafico_ID = conf['SENSORES'][sala]['id'] + '_grafico'
    grafico['id'] = grafico_ID
    grafico['group'] = uiGroup_ID
    grafico['label'] = 'Histórico 1h'
    grafico['name'] = 'grafico (' + conf['SENSORES'][sala]['name'] + ')'
    grafico['x'] = sala_x + 750
    grafico['y'] = sala_y + 50
    
    # Creamos el template que permitirá el cambio de color del grupo en funcion de los umbrales,
    # como hicimos con la función, primero creamos el estilo
    
    estilo="""<style>
              #Panel_de_control_%s{
              text-align: center;
              background-color: {{msg.colorAlerta}};
              color: black;
              }
              </style>""" %(conf['SENSORES'][sala]['name'])
    
    template = jsonPlantilla['TEMPLATE'].copy()
    template_ID = conf['SENSORES'][sala]['id'] + '_template'
    template['id'] = template_ID
    template['group'] = uiGroup_ID
    template['format']= estilo
    template['name'] = 'Template (' + conf['SENSORES'][sala]['name'] + ')'
    template['x'] = sala_x + 500
    template['y'] = sala_y 
     
    
    
    # Ya con los objetos creados, los conectamos entre sí
    
    function['wires']=[["%s"%template_ID]]
    template['wires']=[["%s"%dial_ID,"%s"%grafico_ID]]
    mqttClient['wires']=[["%s"%function_ID]]
    
    
    
    # Añadimos cada uno de los objetos a la lista de objetos JSON
    jsonFinal.append(uiGroup)
    jsonFinal.append(mqttClient)
    jsonFinal.append(function)
    jsonFinal.append(template)
    jsonFinal.append(dial)
    jsonFinal.append(grafico)

    # Ajustamos los valores de posición en el panel de control para la siguiente sala
    
    sala_y += 150


# Grabamos el archivo de salida JSON, eliminando espacios.
# TODO: crear el nombre del archivo a partir de sys.argv
    
nombreJSONSalida='%s.json' %('configuracion_sistema')
    
with open(nombreJSONSalida, 'w') as salida:
    json.dump(jsonFinal, salida)
    
    
    
    


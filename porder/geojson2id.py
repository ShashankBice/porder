__copyright__ = """

    Copyright 2019 Samapriya Roy

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""
__license__ = "Apache 2.0"

#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import json
import os
import csv
import sys
import pyproj
from functools import partial
from shapely.geometry import shape
from shapely.ops import transform
from planet.api.utils import read_planet_json
from planet.api.auth import find_api_key

#Create an empty geojson template
temp={"coordinates":[],"type":"Polygon"}
try:
    PL_API_KEY = find_api_key()
except:
    print('Failed to get Planet Key')
    sys.exit()
SESSION = requests.Session()
SESSION.auth = (PL_API_KEY, '')

ar=[]
far=[]
def handle_page(page,asset,num,outfile,gmain,ovp):
    num=int(num)
    [head,tail]=os.path.split(outfile)
    if num<250:
        try:
            n=0
            open(outfile,'w')
            for items in page['features']:
                for itm in items['_permissions']:
                    if itm.split(':')[0]=="assets."+asset and n<num:
                        it=items.get('id')
                        if items['geometry']['type']=="Polygon":
                            bounds=items['geometry']['coordinates']
                            temp['coordinates']=bounds
                            epsgcode=items['properties']['epsg_code']
                            geom2=shape(temp)
                            if gmain.area>geom2.area:
                                intersect=(geom2).intersection(gmain)
                            elif geom2.area>gmain.area:
                                intersect=(gmain).intersection(geom2)
                            #print('ID '+str(it)+' has percentage overlap: '+str(intersect.area/geommain.area*100))
                            #print(gmain.area)
                            proj = partial(pyproj.transform, pyproj.Proj(init='epsg:4326'),
                                pyproj.Proj(init='epsg:'+str(epsgcode)))
                            ar.append(transform(proj,intersect).area/1000000)
                            far.append(transform(proj,geom2).area/1000000)
                            if (intersect.area/gmain.area)*100>=ovp:
                                # print('ID '+str(it)+' has percentage overlap: '+str(intersect.area/geom2.area*100))
                                n=n+1
                                with open(outfile,'a') as csvfile:
                                    writer=csv.writer(csvfile,delimiter=',',lineterminator='\n')
                                    writer.writerow([it])
            num_lines = sum(1 for line in open(os.path.join(head,tail.split('.')[0]+'.csv')))
            print('Total number of assets written to '+str(os.path.join(head,tail.split('.')[0]+'.csv')+' ===> '+str(num_lines)))
            print('Total estimated cost to quota: '+str("{:,}".format(round(sum(far))))+' sqkm')
            print('Total estimated cost to quota if clipped: '+str("{:,}".format(round(sum(ar))))+' sqkm')
            sys.exit()
        except Exception as e:
            print(e)
    else:
        try:
            n=0
            for items in page['features']:
                for itm in items['_permissions']:
                    if itm.split(':')[0]=="assets."+asset and n<num:
                        it=items.get('id')
                        if items['geometry']['type']=="Polygon":
                            bounds=items['geometry']['coordinates']
                            temp['coordinates']=bounds
                            epsgcode=items['properties']['epsg_code']
                            geom2=shape(temp)
                            if gmain.area>geom2.area:
                                intersect=(geom2).intersection(gmain)
                            elif geom2.area>gmain.area:
                                intersect=(gmain).intersection(geom2)
                            #print('ID '+str(it)+' has percentage overlap: '+str(intersect.area/geommain.area*100))
                            proj = partial(pyproj.transform, pyproj.Proj(init='epsg:4326'),
                                pyproj.Proj(init='epsg:'+str(epsgcode)))
                            ar.append(transform(proj,intersect).area/1000000)
                            far.append(transform(proj,geom2).area/1000000)
                            if (intersect.area/gmain.area)*100>=ovp:
                                # print('ID '+str(it)+' has percentage overlap: '+str(intersect.area/geom2.area*100))
                                n=n+1
                                with open(outfile,'a') as csvfile:
                                    writer=csv.writer(csvfile,delimiter=',',lineterminator='\n')
                                    writer.writerow([it])
            data=csv.reader(open(outfile).readlines()[1: num+2])

            with open(outfile, "w") as f:
                writer = csv.writer(f,delimiter=',',lineterminator='\n')
                for row in data:
                    writer.writerow(row)
        except Exception as e:
            print(e)

def idl(infile,start,end,item,sat,asset,num,cmin,cmax,outfile,ovp):
    [head,tail]=os.path.split(outfile)
    if cmin==None:
        cmin=0
    if cmax==None:
        cmax=1
    if ovp is None:
        ovp=1
    if ovp is not None:
        ovp=int(ovp)
    with open(outfile,'w') as csvfile:
        writer=csv.DictWriter(csvfile,fieldnames=["id"], delimiter=',')
        writer.writeheader()
    open(outfile, 'w')
    headers = {'Content-Type': 'application/json'}
    PL_API_KEY = read_planet_json()['key']

##Parse Geometry
    try:
        if infile.endswith('.geojson'):
            with open(infile) as aoi:
                aoi_resp = json.load(aoi)
                aoi_geom = aoi_resp['features'][0]['geometry']['coordinates']
        elif infile.endswith('.json'):
            with open (infile) as aoi:
                aoi_resp=json.load(aoi)
                aoi_geom=aoi_resp['config'][0]['config']['coordinates']
        elif infile.endswith('.kml'):
            getcoord=kml2coord(infile)
            aoi_geom=getcoord
    except Exception as e:
        print('Could not parse geometry')
        print(e)
## Null payload structure
    if sat==None:
        data = {'filter': {'type': 'AndFilter',
            'config': [{'type': 'GeometryFilter', 'field_name': 'geometry',
            'config': {'type': 'Polygon', 'coordinates': []}},
            {'type': 'OrFilter', 'config': [{'type': 'AndFilter',
            'config': [{'type': 'StringInFilter', 'field_name': 'item_type'
            , 'config': []}, {'type': 'RangeFilter',
            'field_name': 'cloud_cover', 'config': {'gte': [],
            'lte': []}}, {'type': 'RangeFilter',
            'field_name': 'sun_elevation', 'config': {'gte': 0,
            'lte': 90}}]}]}, {'type': 'OrFilter',
            'config': [{'type': 'DateRangeFilter', 'field_name': 'acquired'
            , 'config': {'gte': [],
            'lte': []}}]}]},
            'item_types': []}
        data['filter']['config'][0]['config']['coordinates'] = aoi_geom
        data['filter']['config'][2]['config'][0]['config']['gte'] = str(start)+'T04:00:00.000Z'
        data['filter']['config'][2]['config'][0]['config']['lte'] = str(end)+'T03:59:59.999Z'
        data['filter']['config'][1]['config'][0]['config'][2]['config']['gte'] = float(cmin)
        data['filter']['config'][1]['config'][0]['config'][2]['config']['lte'] = float(cmax)
        data['filter']['config'][1]['config'][0]['config'][0]['config'] = [item]
        data['item_types'] = [item]
        data = str(data).replace("'", '"')
        temp['coordinates']=aoi_geom
        gmain=shape(temp)
    else:
        data = {'filter': {'type': 'AndFilter',
            'config': [{'type': 'GeometryFilter', 'field_name': 'geometry',
            'config': {'type': 'Polygon', 'coordinates': []}},
            {'type': 'OrFilter', 'config': [{'type': 'AndFilter',
            'config': [{'type': 'StringInFilter', 'field_name': 'item_type'
            , 'config': []},{'type': 'StringInFilter', 'field_name': 'satellite_id'
            , 'config': []}, {'type': 'RangeFilter',
            'field_name': 'cloud_cover', 'config': {'gte': [],
            'lte': []}}, {'type': 'RangeFilter',
            'field_name': 'sun_elevation', 'config': {'gte': 0,
            'lte': 90}}]}]}, {'type': 'OrFilter',
            'config': [{'type': 'DateRangeFilter', 'field_name': 'acquired'
            , 'config': {'gte': [],
            'lte': []}}]}]},
            'item_types': []}
    #print(data)
## Configure search payload
        data['filter']['config'][0]['config']['coordinates'] = aoi_geom
        data['filter']['config'][2]['config'][0]['config']['gte'] = str(start)+'T04:00:00.000Z'
        data['filter']['config'][2]['config'][0]['config']['lte'] = str(end)+'T03:59:59.999Z'
        data['filter']['config'][1]['config'][0]['config'][2]['config']['gte'] = float(cmin)
        data['filter']['config'][1]['config'][0]['config'][2]['config']['lte'] = float(cmax)
        data['filter']['config'][1]['config'][0]['config'][1]['config'] = sat
        data['filter']['config'][1]['config'][0]['config'][0]['config'] = [item]
        data['item_types'] = [item]
        data = str(data).replace("'", '"')
        temp['coordinates']=aoi_geom
        gmain=shape(temp)
## Send post request
    querystring = {"strict":"true"}
    result = requests.post('https://api.planet.com/data/v1/quick-search',
                           headers=headers, data=data, params=querystring,
                           auth=(PL_API_KEY, ''))
    page=result.json()
    #print(page)
    final_list = handle_page(page,asset,num,outfile,gmain,ovp)
    while page['_links'].get('_next') is not None:
        page_url = page['_links'].get('_next')
        page = SESSION.get(page_url).json()
        ids = handle_page(page,asset,num,outfile,gmain,ovp)
    num_lines = sum(1 for line in open(os.path.join(head,tail.split('.')[0]+'.csv')))
    print('Total number of assets written to '+str(os.path.join(head,tail.split('.')[0]+'.csv')+' ===> '+str(num_lines)))
    print('Total estimated cost to quota: '+str("{:,}".format(round(sum(far))))+' sqkm')
    print('Total estimated cost to quota if clipped: '+str("{:,}".format(round(sum(ar))))+' sqkm')

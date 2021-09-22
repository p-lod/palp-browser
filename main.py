import html

# https://getbootstrap.com/docs/4.0/examples/sticky-footer-navbar/ is the theme this uses.

# because dominate will stop on html
pyhtml = html

import os
import re
import sys

import pandas as pd

import dominate
from dominate.tags import *
from dominate.util import raw

from bs4 import BeautifulSoup

from flask import Flask, render_template, session, json, request, flash, redirect, url_for, after_this_request

import markdown

import rdflib as rdf
from rdflib.plugins.stores import sparqlstore

#from google.oauth2 import service_account
#from googleapiclient.discovery import build

# install with python3 -m pip install git+https://github.com/p-lod/plodlib
import plodlib

import json

ns = {"dcterms" : "http://purl.org/dc/terms/",
      "owl"     : "http://www.w3.org/2002/07/owl#",
      "rdf"     : "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
      "rdfs"    : "http://www.w3.org/2000/01/rdf-schema#" ,
      "p-lod"   : "urn:p-lod:id:" }

app = Flask(__name__)

# Connect to the remote triplestore with read-only connection
store = rdf.plugin.get("SPARQLStore", rdf.store.Store)(endpoint="http://52.170.134.25:3030/plod_endpoint/query",
                                                       context_aware = False,
                                                       returnFormat = 'json')
g = rdf.Graph(store)

# a 'global' available as a convenience
POMPEII = plodlib.PLODResource('pompeii')

def palp_html_head(r, html_dom):
    html_dom.head += meta(charset="utf-8")
    html_dom.head += meta(http_equiv="X-UA-Compatible", content="IE=edge")
    html_dom.head += meta(name="viewport", content="width=device-width, initial-scale=1")    
    html_dom.head += link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css", integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2", crossorigin="anonymous")
    html_dom.head += script(src="https://code.jquery.com/jquery-3.5.1.slim.min.js", integrity = "sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj", crossorigin="anonymous")
    html_dom.head += script(src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/js/bootstrap.bundle.min.js",integrity="sha384-ho+j7jyWK8fNQe+A12Hb8AhRq26LrZ/JpcUGGOn+Y7RsweNrtN/tE3MoK7ZeZDyx",crossorigin="anonymous")
    html_dom.head += link(rel="stylesheet", href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css", integrity="sha512-xodZBNTC5n17Xt2atTPuE1HxjVMSvLVW9ocqUKLsCC5CXdbqCmblAshOMAS6/keqq/sMZMZ19scR4PsZChSR7A==", crossorigin="")
    html_dom.head += script(src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js", integrity="sha512-XQoYMqMTK8LvdxXYG3nZ448hOEQiglfqkJs1NOQV44cWnUrBc8PkAOcXy20w0vlaXaVUearIOBhiXZ5V3ynxwA==", crossorigin="")
    html_dom.head += script(src="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.2.1/jstree.min.js")
    html_dom.head += link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.2.1/themes/default/style.min.css")
    html_dom.head += link(rel="stylesheet", href="/static/css/tree_style.css")
    html_dom.head += link(rel="stylesheet", href="/static/css/sticky-footer-navbar.css")
    html_dom.head += meta(name="DC.title",lang="en",content=r.identifier )
    html_dom.head += meta(name="DC.identifier", content=f"urn:p-lod:id:{r.identifier}" )

def palp_page_navbar(r, html_dom):
    with html_dom:
      # feature request: suppress a link when displaying the page it links to.
      with header():
        with nav(cls="navbar navbar-expand-md navbar-dark fixed-top bg-dark"):
           a("PALP", href="/browse/pompeii", cls="navbar-brand")
           if r.label:
            span(r.label, cls="navbar-brand")
           elif r.identifier:
            span(r.identifier, cls="navbar-brand")
           else:
            span("Default Page", cls="navbar-brand")
        

        
def palp_page_footer(r, doc):
    with doc:
      with footer(cls="footer"):
        with span():
          small("PALP is hosted at the University of Massachusetts-Amherst and funded by the Getty Foundation.")
          if r.identifier:
            a(f"[view {r.identifier} in p-lod]", href=f"http://p-lod.herokuapp.com/p-lod/id/{r.identifier}")
          if r.p_in_p_url:
              a(" [p-in-p]", href=r.p_in_p_url, target = "_new")
          if r.wikidata_url:
              a(" [wikidata]", href=r.wikidata_url, target = "_new")


# convenience functions
def urn_to_anchor(urn):

  label         = urn.replace("urn:p-lod:id:","") # eventually get the actual label
  relative_url  = f'/browse/{urn.replace("urn:p-lod:id:","")}'

  return relative_url, label

# palp page part renderers

def palp_geojson(r):
  mapdiv = div(id="minimap")
  with mapdiv:
      innerdiv = div(id="minimap-geojson", style="display:none")
      innerdiv += r.geojson

      pompeiidiv = div(id="pompeii-geojson", style="display:none")
      pompeiidiv += POMPEII.geojson

      div(id="minimapid", style="float:right; width: 50%; height: 400px;display:none")
      s = script(type='text/javascript')
      s += raw("""// check if the item-geojson div has content and make a map if it does. 
if ($('#minimap-geojson').html().trim()) {
       $('#minimapid').show()

  var mymap = L.map('minimapid').setView([40.75, 14.485], 16);

  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    id: 'mapbox.streets'
  }).addTo(mymap);

  var pompeii_geojson = L.geoJSON(JSON.parse($('#pompeii-geojson').html()));

  pompeii_geojson.addTo(mymap);
  mymap.fitBounds(pompeii_geojson.getBounds());

       features = L.geoJSON(JSON.parse($('#minimap-geojson').html()), {
       style: {"color":"red"},
  onEachFeature: function (feature, layer) {
    var id_no_urn = feature.properties.title;
    id_no_urn = id_no_urn.replace("urn:p-lod:id:","");
    layer.bindPopup('<a href="/browse/'+id_no_urn+'">'+id_no_urn+'</a>');
    
    //layer.on('click', function (e) {
        //console.log('/browse/'+id_no_urn);
        //window.open('/browse/'+id_no_urn,"_self");
    //});
    
    layer.bindTooltip(id_no_urn);
  }
})
       features.addTo(mymap);

       

       
       
}""")

  return mapdiv

def palp_spatial_hierarchy(r):
  ditop = div(id="alljstree")
  with ditop:
    di = div(id="jstree")
    # with di:
    #   ul(li("root"))
    with di:
      element = ul(cls="tree")
      with element:
        hier_up = r.spatial_hierarchy_up()
        if len(hier_up) >= 1:
          relative_url, label = urn_to_anchor(hier_up[-1][0])
          li(a(label, href=relative_url))
        if len(hier_up) >= 2:
          wb = ul()
          with wb:
            relative_url, label = urn_to_anchor(hier_up[-2][0])
            li(a(label, href=relative_url))
            if len(hier_up) >= 3:
              wc = ul()
              with wc:
                relative_url, label = urn_to_anchor(hier_up[-3][0])
                li(a(label, href=relative_url))
                if len(hier_up) >= 4:
                  wd = ul()
                  with wd:
                    relative_url, label = urn_to_anchor(hier_up[-4][0])
                    li(a(label, href=relative_url))
                    if len(hier_up) >= 5:
                      we = ul()
                      with we:
                        relative_url, label = urn_to_anchor(hier_up[-5][0])
                        li(a(label, href=relative_url))
            
    # s = script(type='text/javascript')
    # s += """$(function () {
    #   // 6 create an instance when the DOM is ready
    #   $('#jstree').jstree();
    #   });"""
  return ditop

def palp_spatial_children(r):

  element = span()
  with element:
    for i in r.spatial_children():
      relative_url, label = urn_to_anchor(i[0])
      a(label, href=relative_url)
      span(" /", style="color: LightGray")
  return element

def palp_depicted_by_images(r):

  element = span()
  with element:
    for i in r.images_luna_labels:
      # relative_url, label = urn_to_anchor(i[0])
      a(i, href=f'https://umassamherst.lunaimaging.com/luna/servlet/view/search?search=SUBMIT&cat=0&q={i[0]}&dateRangeStart=&dateRangeEnd=&sort=mediafileName%2Caddress%2Ccreator&QuickSearchA=QuickSearchA')
      span(" /", style="color: LightGray")
  return element

def palp_depicts_concepts(r):

  element = span()
  with element:
    for i in r.depicts_concepts():
      relative_url, label = urn_to_anchor(i[0])
      a(label, href=relative_url)
      span(" /", style="color: LightGray")
  return element

def palp_depicted_where(r):

  element = span()
  with element:
    for i in r.depicted_where():
      relative_url, label = urn_to_anchor(i[0])
      a(label, href=relative_url)
      span(" /", style="color: LightGray")
  return element


# type renderers
def city_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):
      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)
      
      with div(id="spatial_children"):
        span("Regions and Streets Within:")
        palp_spatial_children(r)

      with div(id="depicts_concepts"):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)
          


def region_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):

      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="spatial_hierarchy"):
        span("Spatial Hierarchy: ")
        palp_spatial_hierarchy(r)

      with div(id="spatial_children"):
        span("Insula and Streets Within: ")
        palp_spatial_children(r)

      with div(id="depicts_concepts: "):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)


def insula_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):

      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="spatial_hierarchy"):
        span("Spatial Hierarchy: ")
        palp_spatial_hierarchy(r)

      with div(id="spatial_children"):
        span("Properties Within: ")
        palp_spatial_children(r)

      with div(id="depicts_concepts: "):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)


def property_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):

      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="spatial_hierarchy"):
        span("Spatial Hierarchy: ")
        palp_spatial_hierarchy(r)

      with div(id="spatial_children"):
        span("Spaces (aka 'Rooms') Within: ")
        palp_spatial_children(r)

      with div(id="depicts_concepts: "):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)


def space_render(r,html_dom):

    with html_dom:
      with main(cls="container", role="main"):

        if r.geojson:
          with div(id="geojson"):
            palp_geojson(r)

        with div(id="spatial_hierarchy"):
          span("Spatial Hierarchy: ")
          palp_spatial_hierarchy(r)

        with div(id="spatial_children"):
          span("Features Within: ")
          palp_spatial_children(r)

        with div(id="depicts_concepts: "):
          span("Depicts Concepts: ")
          palp_depicts_concepts(r)


def feature_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):
      ar = r.identifier
   
      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)[0:20]

      with div(id="spatial_hierarchy"):
        span("Spatial Hierarchy: ")
        palp_spatial_hierarchy(r)

      with div(id="depicts_concepts"):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)

      with div(id="images"):
        span("Images: ")
        palp_depicted_by_images(r)


def artwork_render(r,html_dom):

  with html_dom:

    if r.geojson:
      with div(id="geojson"):
        palp_geojson(r)

    with div(id="spatial_hierarchy"):
      span("Spatial Hierarchy: ")
      palp_spatial_hierarchy(r)

    with div(id="depicts_concepts: "):
      span("Depicts Concepts: ")
      palp_depicts_concepts(r)


def concept_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):

      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="depicted_where"):
        span("Depicted in the following Pompeian spaces: ")
        palp_depicted_where(r)


def street_render(r,html_dom):

  with html_dom:

    if r.geojson:
      with div(id="geojson"):
        r.geojson[0:20]

    with div(id="spatial_hierarchy"):
      span("Spatial Hierarchy: ")
      for i in r.spatial_hierarchy_up():
        relative_url, label = urn_to_anchor(i[0])
        a(f"{label} / ", href=relative_url)



def unknown_render(r,html_dom):

  with html_dom:
    span(f"Unknown type.")



def palp_html_document(r,renderer):

  html_dom = dominate.document(title=f"Pompeii Artistic Landscape Project: {r.identifier}" )

  palp_html_head(r, html_dom)
  html_dom.body
  palp_page_navbar(r,html_dom)

  renderer(r, html_dom)

  palp_page_footer(r, html_dom)

  return html_dom


# The PALP Verbs that Enable Navigation

@app.route('/start')
def palp_start():
  r = plodlib.PLODResource("Pompeii")
  html_dom = dominate.document(title=f"Pompeii Artistic Landscape Project" )

  palp_html_head(r, html_dom)
  html_dom.body
  palp_page_navbar(r,html_dom)

  with html_dom:
    with div(id="page-content-wrapper"):
      with div(id="container-fluid"):
        pi = p("""Useful, appealing, and explanatory start page that looks like a PALP page.
    Eric Poehler (UMass), Director and Sebastian Heath (NYU/ISAW), Co-Director. Funded by Getty Foundation. Etc., etc., etc.
    """)
        pi.add(a("Pompeii", href="/browse/pompeii"))

  palp_page_footer(r, html_dom)
  return html_dom.render()

@app.route('/browse/<path:identifier>')
def palp_browse(identifier):

  r = plodlib.PLODResource(identifier)

  try:
    return palp_html_document(r, globals()[f'{r.rdf_type}_render']).render() # call p_h_d with right render function if it exists
  except KeyError as e:
    return palp_html_document(r,unknown_render).render()

@app.route('/map/')
def palp_map():
    return """Super cool and useful map page. What should it do? <a href="/start">Start</a>."""

@app.route('/search/')
def palp_search():
    return """Super cool and useful search page. What should it do? <a href="/start">Start</a>."""

@app.route('/')
def index():
    return redirect("/browse/pompeii", code=302)


#### SQL AND BOX STUFF
#
## MySQL configurations using environment variables
#app.config['MYSQL_USER'] = os.environ['MYSQL_USER']
#app.config['MYSQL_PASSWORD'] = os.environ['MYSQL_PASSWORD']
#app.config['MYSQL_DB'] = os.environ['MYSQL_USER']
#app.config['MYSQL_HOST'] = os.environ['MYSQL_HOST']
#mysql = MySQL(app)
##
##Box API configurations using environment variables
#box_auth = boxsdk.JWTAuth(
#    client_id=str(os.environ["BOX_ID"]),
#    client_secret=str(os.environ["BOX_SECRET"]),
#    enterprise_id=str(os.environ["BOX_ENTERPRISE"]),
#    jwt_key_id=str(os.environ["BOX_PUBLIC_KEY"]),
#    rsa_private_key_data=str(os.environ["BOX_PRIVATE_KEY"]).replace("||n||", "\n").replace("beginnnn", "BEGIN ENCRYPTED PRIVATE KEY").replace("endddd", 'END ENCRYPTED PRIVATE KEY'),
#    rsa_private_key_passphrase=str(os.environ["BOX_PASSPHRASE"])
#)
#
#box_access_token = box_auth.authenticate_instance()
#box_client = boxsdk.Client(box_auth)

 #  totimgs = {}
#    pinpCur = mysql.connection.cursor()
#    pinpQuery = "SELECT  `archive_id`, `hero_image` FROM `PinP_preq` WHERE `ARC`='" + ar +"' OR `other_ARC` LIKE '%" + ar + "%';"
#    pinpCur.execute(pinpQuery)
#    pinpdata = pinpCur.fetchall()
#    pinpCur.close()
#    for d in pinpdata:
#      indpinp = {}
#      if str(d[1]) == "1":
#        indpinp['is_hero'] = True
#      else:
#        indpinp['is_hero'] = False
#      assocCur = mysql.connection.cursor()
#      assocQuery = "SELECT DISTINCT `id_box_file`, `img_alt` FROM `PinP` WHERE `archive_id` = '"+str(d[0])+"' ORDER BY `img_url`;"
#      assocCur.execute(assocQuery)
#      all0 = assocCur.fetchall()
#      indpinp['description'] = all0[0][1]
#      indpinp['box_id'] = all0[0][0]
#      assocCur.close()
#      totimgs[d[0]] = indpinp
#    ppmCur = mysql.connection.cursor()
#    ppmQuery = "SELECT  `id`, `hero_image` FROM `PPM_preq` WHERE `ARC`='" + ar +"' OR `other_ARC` LIKE '%" + ar + "%';"
#    ppmCur.execute(ppmQuery)
#    ppmdata = ppmCur.fetchall()
#    ppmCur.close()
#    for d in ppmdata:
#      indppm = {}
#      if str(d[1]) == "1":
#        indppm['is_hero'] = True
#      else:
#        indppm['is_hero'] = False
#      assocCur = mysql.connection.cursor()
#      assocQuery = "SELECT DISTINCT `image_id`, `translated_text` FROM `PPM` WHERE `id` = '"+str(d[0])+"';"
#      assocCur.execute(assocQuery)
#      all0 = assocCur.fetchall()
#      indppm['description'] = all0[0][1]
#      indppm['box_id'] = all0[0][0]
#      assocCur.close()
#      totimgs[d[0]] = indppm
#


#    with div(id="images"):
#      span("Images: ")
#      element = span()
#      with element:
#        for i in totimgs:
#          # try:
#          #   boxlink = box_client.file(totimgs[i]['box_id']).get_shared_link(access='collaborators')
#          # except boxsdk.BoxAPIException as exception:
#          #   boxlink=exception
#          # div(raw("""<iframe
#          #   src="{}?view=icon"
#          #   frameborder="0"
#          #   allowfullscreen
#          #   webkitallowfullscreen
#          #   msallowfullscreen
#          # ></iframe>""".format(boxlink)))
#          boxlink = "https://app.box.com/file/"+str(totimgs[i]['box_id'])
#          a(totimgs[i]['description'], href=boxlink)
#          if totimgs[i]['is_hero']:
#            span("-- is hero")
#          br()    
##
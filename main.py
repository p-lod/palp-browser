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

      div(id="minimapid", style="float:right; width: 40%; height: 400px;display:none")
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

  element = div()

  hier_up = r.spatial_hierarchy_up()

  for i,h in enumerate(hier_up):
    relative_url, label = urn_to_anchor(h[0])

    if i == 0:
      span(label)
    else:
      a(label, href=relative_url)

    if i < (len(hier_up)-1):
      if i == 0:
        span(" is within ")
      else:
        span(" → ")

  return element

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

def palp_spatial_children(r, images = False):

  element = span()
  with element:
    for i,c in enumerate(r.spatial_children()):
      #relative_url, label = urn_to_anchor(i[0])
      #a(label, href=relative_url)
      #span(" /", style="color: LightGray")
      with table(style="border: 1px solid black;margin-top:5px"):
        with tr():
          with td(style="padding-top:5px"):
            relative_url, label = urn_to_anchor(c[0])
            a(label, href=relative_url)
        
      if (images and (i < 10)):
        with tr():
          with td(colspan=3):
            get_first_image_of = c[0].replace("urn:p-lod:id:","")
            palp_depicted_by_images(plodlib.PLODResource(get_first_image_of), first_only = True)
  
  return element

def palp_depicted_by_images(r, first_only = False):

  luna_images_l = r.images_from_luna

  element = div()
  with element:
    if first_only:
      if len(luna_images_l):
        #iframe(id="widgetPreview", frameBorder="0", width="500px", height="350px", border="0px", style="border:0px solid white", src=f"https://umassamherst.lunaimaging.com/luna/servlet/detail/{luna_images_l[0][1]}?embedded=true&cic=umass%7E14%7E14&widgetFormat=javascript&widgetType=detail&controls=1&nsip=1")
        iframe(width="500px", height="350px", src=f"https://umassamherst.lunaimaging.com/luna/servlet/workspace/handleMediaPlayer?lunaMediaId={luna_images_l[0][1]}",title="Image from Luna", allow="fullscreen")
        with div(style="width:500px"):
          span(luna_images_l[0][3])
          span(' [')
          a("about image...",href=f"https://umassamherst.lunaimaging.com/luna/servlet/detail/{luna_images_l[0][1]}")
          span("]")
    
    else:
      for i in luna_images_l:
        iframe(width="500px", height="350px", src=f"https://umassamherst.lunaimaging.com/luna/servlet/workspace/handleMediaPlayer?lunaMediaId={i[1]}",title="Image from Luna", allow="fullscreen")
        with div(style="width:500px; margin-bottom:5px"):
          span(luna_images_l[0][3])
          span(' [')
          a("about image...",href=f"https://umassamherst.lunaimaging.com/luna/servlet/detail/{luna_images_l[0][1]}")
          span("]")

        #iframe(id="widgetPreview", frameBorder="0", width="500px", height="350px", border="1px", style="border:1px solid black", src=f"https://umassamherst.lunaimaging.com/luna/servlet/detail/{i[1]}?embedded=true&cic=umass%7E14%7E14&widgetFormat=javascript&widgetType=detail&controls=1&nsip=1")
        #<iframe id="widgetPreview",frameBorder="0", width="700px", height="350px", border="0px", style="border:0px solid white", src="https://umassamherst.lunaimaging.com/luna/servlet/detail/umass~14~14~99562~1272567?embedded=true&cic=umass%7E14%7E14&widgetFormat=javascript&widgetType=detail&controls=1&nsip=1" ></iframe>

        #img(src=i[1], style="max-width:300px;margin-top:3px")

        br()

  return element

def palp_depicts_concepts(r):

  element = span()
  with element:
    for i in r.depicts_concepts():
      relative_url, label = urn_to_anchor(i[0])
      a(label, href=relative_url)
      span(" /", style="color: LightGray")
  return element

def palp_depicted_where(r, level_of_detail = 'feature'):

  element = div()
  with element:
    for i in r.depicted_where(level_of_detail=level_of_detail):
      with table(style="border: 1px solid black;margin-top:5px"):
        with tr():
          with td(style="padding-top:5px"):
            relative_url, label = urn_to_anchor(i[3])
            span("Within ")
            a(label, href=relative_url)
            span(" on wall or feature:")
          with td(style="padding-top:5px"):
            relative_url, label = urn_to_anchor(i[0])
            a(label, href=relative_url)
          
        with tr():
          with td(colspan=2):
            get_first_image_of = i[0].replace("urn:p-lod:id:","")
            palp_depicted_by_images(plodlib.PLODResource(get_first_image_of), first_only = True)


  return element


# type renderers
def city_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):
      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="depicts_concepts"):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)
      
      with div(id="spatial_children"):
        span("Insula and Streets Within: ")
        palp_spatial_children(r, images = False)


          


def region_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):

      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="spatial_hierarchy", style="margin-bottom:.5em"):
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

      with div(id="spatial_hierarchy", style="margin-bottom:1em"):
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

      with div(id="spatial_hierarchy", style="margin-bottom:1em"):
        palp_spatial_hierarchy(r)

      with div(id="depicts_concepts: "):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)

      with div(id="spatial_children"):
        span("Spaces (aka 'Rooms') Within: ")
        palp_spatial_children(r, images = False)




def space_render(r,html_dom):

    with html_dom:
      with main(cls="container", role="main"):

        if r.geojson:
          with div(id="geojson"):
            palp_geojson(r)

        with div(id="spatial_hierarchy", style="margin-bottom:1em"):
          palp_spatial_hierarchy(r)

        with div(id="depicts_concepts: "):
          span("Depicts Concepts: ")
          palp_depicts_concepts(r)

        with div(id="spatial_children"):
          span("Features Within: ")
          palp_spatial_children(r, images = True)



def feature_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):
      ar = r.identifier

      if r.geojson:
          with div(id="geojson"):
            palp_geojson(r)

      with div(id="spatial_hierarchy", style="margin-bottom:1em"):
        palp_spatial_hierarchy(r)

      with div(id="depicts_concepts"):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)

      with div(id="images"):
        br()
        palp_depicted_by_images(r)


def artwork_render(r,html_dom):

  with html_dom:

    if r.geojson:
      with div(id="geojson"):
        palp_geojson(r)

    with div(id="spatial_hierarchy", style="margin-bottom:1em"):
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
          span(raw(f"<b>'{r.identifier}'</b> is depicted"))
          palp_depicted_where(r)


def street_render(r,html_dom):

  with html_dom:

    if r.geojson:
      with div(id="geojson"):
        r.geojson[0:20]

    with div(id="spatial_hierarchy", style="margin-bottom:1em"):
      palp_spatial_hierarchy(r)


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

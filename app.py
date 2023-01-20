import html

# https://getbootstrap.com/docs/4.0/examples/sticky-footer-navbar/ is the theme this uses.

# because dominate will stomp on html
py_html = html

import json
import os
import re
import sys

from urllib.request import urlopen

import pandas as pd

import dominate
from dominate.tags import *
from dominate.util import raw

from bs4 import BeautifulSoup

from flask import Flask, render_template, session, json, request, flash, redirect, url_for, after_this_request

import markdown

import rdflib as rdf
from rdflib.plugins.stores.sparqlstore import SPARQLStore

from shapely.geometry import shape, mapping
from shapely.affinity import translate

from string import Template

import plodlib

ns = {"dcterms" : "http://purl.org/dc/terms/",
      "owl"     : "http://www.w3.org/2002/07/owl#",
      "rdf"     : "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
      "rdfs"    : "http://www.w3.org/2000/01/rdf-schema#" ,
      "p-lod"   : "urn:p-lod:id:" }

app = Flask(__name__)


# Connect to the remote triplestore with read-only connection
store = SPARQLStore(endpoint="http://52.170.134.25:3030/plod_endpoint/query",
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
    html_dom.head += script(src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js", integrity="sha512-894YE6QWD5I59HgZOGReFYm4dnWc1Qt5NtvYSaNcOP+u1T9qYdvdihz0PPSiiqn/+/3e7Jo4EaG7TubfWGUrMQ==", crossorigin="anonymous", referrerpolicy="no-referrer")
    html_dom.head += script(src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/galleria.min.js", integrity="sha512-vRKUU1GOjCKOTRhNuhQelz4gmhy6NPpB8N41c7a36Cxl5QqKeB9VowP8S7x8Lf3B8vZVURBxGlPpvyiRHh+CKg==",crossorigin="anonymous",referrerpolicy="no-referrer")
    html_dom.head += script(src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/js/bootstrap.bundle.min.js",integrity="sha384-ho+j7jyWK8fNQe+A12Hb8AhRq26LrZ/JpcUGGOn+Y7RsweNrtN/tE3MoK7ZeZDyx",crossorigin="anonymous")
    html_dom.head += link(rel="stylesheet", href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css", integrity="sha512-xodZBNTC5n17Xt2atTPuE1HxjVMSvLVW9ocqUKLsCC5CXdbqCmblAshOMAS6/keqq/sMZMZ19scR4PsZChSR7A==", crossorigin="")
    html_dom.head += script(src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js", integrity="sha512-XQoYMqMTK8LvdxXYG3nZ448hOEQiglfqkJs1NOQV44cWnUrBc8PkAOcXy20w0vlaXaVUearIOBhiXZ5V3ynxwA==", crossorigin="")
    html_dom.head += link(rel="stylesheet", href="/static/css/sticky-footer-navbar.css")
    html_dom.head += meta(name="DC.title",lang="en",content=r.identifier )
    html_dom.head += meta(name="DC.identifier", content=f"urn:p-lod:id:{r.identifier}" )


def palp_page_navbar(r, html_dom):
    with html_dom:
      # feature request: suppress a link when displaying the page it links to.
      with header():
        with nav(cls="navbar navbar-expand-md navbar-dark fixed-top bg-dark"):
          img(src="/static/images/under-construction.png", style="width:35px")
          span(raw("&nbsp;"))
          a("PALP", href="/start", cls="navbar-brand")
          if r.label:
           span(r.label, cls="navbar-brand")
          elif r.identifier:
           if r.rdf_type is not None:
            span(f"{r.rdf_type} ", cls="navbar-brand")
           span(r.identifier, cls="navbar-brand")
          else:
           span("", cls="navbar-brand")
          
          p_in_p = json.loads(r.get_predicate_values('urn:p-lod:id:p-in-p-url'))
          if p_in_p:
            with span(cls="navbar-brand"):
              span(" [")
              a("Pompeii in Pictures", href= p_in_p[0])
              span("]")

          wiki_en = json.loads(r.get_predicate_values('urn:p-lod:id:wiki-en-url'))
          if wiki_en:
            with span(cls="navbar-brand"):
              span(" [")
              a("Wiki (en)", href= wiki_en[0])
              span("]")
              
          wiki_it = json.loads(r.get_predicate_values('urn:p-lod:id:wiki-it-url'))
          if wiki_it:
            with span(cls="navbar-brand"):
              span(" [")
              a("Wiki (it)", href= wiki_it[0])
              span("]")
          
          pleiades = json.loads(r.get_predicate_values('urn:p-lod:id:pleiades-url'))
          if pleiades:
            with span(cls="navbar-brand"):
              span(" [")
              a("Pleiades", href= pleiades[0])
              span("]")
        
          with form(cls="navbar-form navbar-right", role="search", action="/full-text-search"):
                        with span(cls="form-group"):
                            input_(id="q", name="q", type="text",cls="form-control",placeholder="Keyword Search...")

        
def palp_page_footer(r, doc):
    with doc:
      with footer(cls="footer"):
        with span():
          small("PALP is hosted at the University of Massachusetts-Amherst and funded by the Getty Foundation. The site is very much in development and will change regularly.")


# convenience functions
def urn_to_anchor(urn):

  label         = urn.replace("urn:p-lod:id:","") # eventually get the actual label
  relative_url  = f'/browse/{urn.replace("urn:p-lod:id:","")}'

  return relative_url, label

def luna_tilde_val(luna_urn):
  if luna_urn.startswith("urn:p-lod:id:luna_img_PALP"):
    tilde_val = "14"

  if luna_urn.startswith("urn:p-lod:id:luna_img_PPM"):
    tilde_val = "16"

  return tilde_val

def img_src_from_luna_info(l_collection_id, l_record, l_media):
  
  img_src = None #default if no URLs present (probably means LUNA doesn't have image though triplestore thinks it does)
  img_description = None
  
  luna_json = json.loads(urlopen(f'https://umassamherst.lunaimaging.com/luna/servlet/as/fetchMediaSearch?mid={l_collection_id}~{l_record}~{l_media}&fullData=true').read())
  
  if len(luna_json):

    img_attributes = json.loads(luna_json[0]['attributes'])

    if 'image_description_english' in img_attributes.keys():
      img_description = img_attributes['image_description_english']
    else:
      try:
        if l_collection_id == 'umass~14~14':
          img_description = json.loads(luna_json[0]['fieldValues'])[2]['value']
        elif l_collection_id == 'umass~16~16':
          img_description = json.loads(luna_json[0]['fieldValues'])[1]['value']
        else:
          img_description = f"unrecognized collection {l_collection_id}"
      except:
        img_description = "Trying to get description failed"
    

    if 'urlSize4' in img_attributes.keys(): # use size 4, sure, but only if there's nothing else
      img_src = img_attributes['urlSize4']
    if 'urlSize2' in img_attributes.keys(): # preferred
      img_src = img_attributes['urlSize2']
    elif 'urlSize3' in img_attributes.keys():
      img_src = img_attributes['urlSize3']
    else:
      img_src = img_attributes['urlSize1']

  return img_src, img_description

def galleria_inline_script():
  s = script(type="text/javascript")
  s += raw("""(function() {
                Galleria.loadTheme('https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/twelve/galleria.twelve.min.js');
                Galleria.configure({debug: false,
                                    lightbox: true,
                                    imageCrop: false , 
                                    carousel: false,
                                    dataConfig: function(img) {
        return {
            title: $(img).next('h2').html(), // tell Galleria to use the h2 as title
            description: $(img).siblings('.desc').html() // tell Galleria to grab the content from the .desc div as caption
        };
    }})
                Galleria.on('image', function(e) {
                  $('#galleria-display').html($(e.currentTarget).find('.galleria-info-description').html());
                  // Galleria.log($(e.currentTarget).find('.galleria-info-description').html())
                  });

                Galleria.run('.galleria');
            }());
""")
  return s
 

def adjust_geojson(geojson_str, rdf_type = None): # working on shifting geojson .00003 to the N  

  # offsets

  xoff = 0
  yoff =  0
  if rdf_type == "region":
    yoff = 0 

  # xoff = -0.0000075
  # yoff =  0.000037
  # if rdf_type == "region":
  #   yoff = .00072




  g = json.loads(geojson_str)
  if g['type'] == 'FeatureCollection':
    for f in g['features']:
      s =  shape(f['geometry'])
      f['geometry'] = mapping(translate(s, xoff=xoff, yoff=yoff, zoff=0.0))
    return json.dumps(g)

  elif g['type'] == 'Feature':
    s =  shape(g['geometry'])
    g['geometry'] = mapping(translate(s, xoff=xoff, yoff=yoff, zoff=0.0))
    return json.dumps(g)
  else:
    return geojson_str

# palp page part renderers

def palp_image_gallery(r):
  
  try:
    r_images = json.loads(r.gather_images())
  except:
    return
  
  with div( _class="galleria", style="width: 80%; height:400px; background: #000"):
    for i in r_images:
      if i['l_img_url']:
        tilde_val = luna_tilde_val(i['urn'])
        with div(_class="image"):
          img(src = i['l_img_url'], loading="lazy")
          h2("", style="color:white")
          with div(_class = "desc"):
            with div():
              if ('feature' in i) and (r.rdf_type == 'concept'):
                b(r.identifier)
                span(" appears on feature: ")
                relative_url, label = urn_to_anchor(i['feature'])
                a(label,href=relative_url)
                span(". ")

                c_feature = i['feature'].replace("urn:p-lod:id:","")
                c_r = plodlib.PLODResource(c_feature)
                
                if len(json.loads(c_r.spatially_within)) > 0:
                  span("Within ")
                  relative_url, label = urn_to_anchor(json.loads(c_r.spatially_within)[0]['urn'])
                  a(label,href=relative_url)
                  span(".")
                  br()
                  span(f"Feature depicts: ")
                  palp_depicts_concepts(c_r)
                else:
                  print(f'Image gallery no spatially within: {c_feature}')
              
            div(i['l_description'])
            with div():
              span('[')
              a("Image credits and additional info...",href=f"/browse/{i['urn'].replace('urn:p-lod:id:','')}")
              span('] ')


def palp_geojson(r):
  mapdiv = div(id="minimap")
  with mapdiv:
      innerdiv = div(id="minimap-geojson", style="display:none")
      if bool(r.geojson):
        innerdiv += adjust_geojson(r.geojson, rdf_type=r.rdf_type)
      elif bool(json.loads(r.spatially_within)):
        within_json = json.loads(r.spatially_within)[0]
        within_identifier = within_json['urn'].replace("urn:p-lod:id:","")
        within_rdf_type = plodlib.PLODResource(within_identifier).rdf_type
        innerdiv += adjust_geojson(within_json['geojson'],
                                   rdf_type = within_rdf_type)
      else:
        innerdiv += ''

      pompeiidiv = div(id="pompeii-geojson", style="display:none")
      pompeiidiv += POMPEII.geojson

      withindiv = div(id="within-geojson", style="display:none")
      if bool(json.loads(r.spatially_within)):
        within_json = json.loads(r.spatially_within)[0]
        within_identifier = within_json['urn'].replace("urn:p-lod:id:","")
        within_rdf_type = plodlib.PLODResource(within_identifier).rdf_type
        withindiv += adjust_geojson(within_json['geojson'],
                                   rdf_type = within_rdf_type)


      div(id="minimapid", style=" width: 80%; height: 400px;display:none")
      s = script(type='text/javascript')
      s += raw("""// check if the item-geojson div has content and make a map if it does. 
if ($('#minimap-geojson').html().trim()) {
      // fit to resource starts as true, will get set to false if ther eis within_geojson
      var fit_to_resource = true;
       $('#minimapid').show()

  var mymap = L.map('minimapid').setView([40.75, 14.485], 16);

  // L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    L.tileLayer('http://palp.art/xyz-tiles/{z}/{x}/{y}.png', {
    maxZoom: 20,
    attribution: 'Pompeii Bibliography and Mapping Project',
    id: 'pbmp',
    tms: false
  }).addTo(mymap);

  // var pompeii_geojson = L.geoJSON(JSON.parse($('#pompeii-geojson').html()));
  //pompeii_geojson.addTo(mymap);
  //mymap.fitBounds(pompeii_geojson.getBounds());
  mymap.fitBounds([[14.478462923715377,40.74778073661396],[14.496141013817796,40.754123872267314]])
  //console.log(pompeii_geojson.getBounds().toBBoxString())


   if ($('#within-geojson').html().trim()) { 
    var within_geojson = L.geoJSON(JSON.parse($('#within-geojson').html()), {
       style: {"color":"yellow", "opacity": 0, "fillOpacity": .4}})
  //onEachFeature: function (feature, layer) {
    //var id_no_urn = feature.id;
    //console.log('/browse/'+id_no_urn);
    //id_no_urn = id_no_urn.replace("urn:p-lod:id:","");
    //layer.bindPopup('<a href="/browse/'+id_no_urn+'">'+id_no_urn+'</a>');
    
    //layer.on('click', function (e) {
        //console.log('/browse/'+id_no_urn);
        //window.open('/browse/'+id_no_urn,"_self");
    //});
    
    //layer.bindTooltip(id_no_urn);
  //}
  //     });
    within_geojson.addTo(mymap);
    mymap.fitBounds(within_geojson.getBounds());
    fit_to_resource = false;
    }


       features = L.geoJSON(JSON.parse($('#minimap-geojson').html()), {
       style: {"color":"red", "weight": 1, "fillOpacity":.5},
  onEachFeature: function (feature, layer) {
    var id_no_urn = feature.properties.title;
    id_no_urn = id_no_urn.replace("urn:p-lod:id:","");
    layer.bindPopup('<a href="/browse/'+id_no_urn+'">'+id_no_urn+'</a>');
    
    //layer.on('click', function (e) {
        //console.log('/browse/'+id_no_urn);
        //window.open('/browse/'+id_no_urn,"_self");
    //});
    
    //layer.bindTooltip(id_no_urn);
  }
})
       features.addTo(mymap);
       if (fit_to_resource) { mymap.fitBounds(features.getBounds()); }

       

       
       
}""")

  return mapdiv

def palp_spatial_hierarchy(r):

  # element = div()

  hier_up = json.loads(r.spatial_hierarchy_up())

  for i,h in enumerate(hier_up):
    relative_url, label = urn_to_anchor(h['urn'])

    if i == 0:
      span(label)
    elif i < (len(hier_up)-1):
      a(label, href=relative_url)
    else:
      a(f"{label}.", href=relative_url)

    if i < (len(hier_up)-1):
      if i == 0:
        span(" is within ")
      else:
        span(" → ")

  # return element


def palp_spatial_children(r, images = False):

  element = span()
  with element:
    for i,c in enumerate(json.loads(r.spatial_children())):
      relative_url, label = urn_to_anchor(c['urn'])
      a(label, href=relative_url)
      span(" /", style="color: LightGray")

      # with table(style="border: 1px solid black;margin-top:5px"):
      #   with tr():
      #     with td(style="padding-top:5px"):
      #       relative_url, label = urn_to_anchor(c['urn'])
      #       a(label, href=relative_url)
        
      # if (images and (i < 10)):
      #   with tr():
      #     with td(colspan=3):
      #       get_first_image_of = c['urn'].replace("urn:p-lod:id:","")
      #       palp_depicted_by_images(plodlib.PLODResource(get_first_image_of), first_only = True)
  
  return element

def palp_depicted_by_images(r, first_only = False):

  luna_images_j = json.loads(r.images_from_luna)

  element = div()
  with element:
    if first_only:
      if len(luna_images_j):
        tilde_val = luna_tilde_val(luna_images_j[0]['urn'])

        img_src,img_description = img_src_from_luna_info(l_collection_id = f'umass~{tilde_val}~{tilde_val}',
                                                 l_record = luna_images_j[0]['l_record'],
                                                 l_media  = luna_images_j[0]['l_media'])
        img(src=img_src)

        with div(style="width:500px"):
          span(str(img_description))
          span(' [')
          a("about image...",href=f"https://umassamherst.lunaimaging.com/luna/servlet/detail/umass~{tilde_val}~{tilde_val}~{luna_images_j[0]['l_record']}~{luna_images_j[0]['l_media']}")
          span("]")
          
    
    else:
      for i in luna_images_j:
        tilde_val = luna_tilde_val(i['urn'])
        
        img_src,img_description = img_src_from_luna_info(l_collection_id = f'umass~{tilde_val}~{tilde_val}',
                                                 l_record = i['l_record'],
                                                 l_media  = i['l_media'])

        img(src=img_src)
        
        with div(style="width:500px; margin-bottom:5px"):
          span(str(img_description))
          span(' [')
          a("about image...",href=f"https://umassamherst.lunaimaging.com/luna/servlet/detail/umass~{tilde_val}~{tilde_val}~{i['l_record']}~{i['l_media']}")
          span("]")
        br()

  return element

def palp_depicts_concepts(r):

  element = span()
  with element:
    for i in json.loads(r.depicts_concepts()):
      relative_url, label = urn_to_anchor(i['urn'])
      a(label, href=relative_url)
      span(" /", style="color: LightGray")
  return element

def palp_depicted_where(r, level_of_detail = 'feature'):
  element = span()
  with element:
    for i,c in enumerate(json.loads(r.depicted_where(level_of_detail=level_of_detail))):
      relative_url, label = urn_to_anchor(c['urn'])
      a(label, href=relative_url)
      span(" /", style="color: LightGray")




    # for i,row in pd.DataFrame(data = json.loads(r.depicted_where(level_of_detail=level_of_detail))).iterrows():
    #   with table(style="border: 1px solid black;margin-top:5px"):
    #     with tr():
    #       with td(style="padding-top:5px"):
    #         relative_url, label = urn_to_anchor(row['within'])
    #         span("Within ")
    #         a(label, href=relative_url)
    #         span(" on wall or feature:")
    #       with td(style="padding-top:5px"):
    #         relative_url, label = urn_to_anchor(row['urn'])
    #         a(label, href=relative_url)

    #     with tr():
    #       if row['best_image'] != 'None': # Has a best image
    #         tilde_val = luna_tilde_val(row['best_image'])
      
    #         with td(colspan=2):
              
    #           img_src,img_description = img_src_from_luna_info(l_collection_id = f'umass~{tilde_val}~{tilde_val}',
    #                                              l_record = row['l_record'],
    #                                              l_media  = row['l_media'])
    #           img(src=img_src)

    #           with div(style="width:500px"):
    #             span(str(img_description))
    #             span(' [')
    #             a(f"about image {row['best_image']}...",href=f"https://umassamherst.lunaimaging.com/luna/servlet/detail/umass~{tilde_val}~{tilde_val}~{row['l_record']}~{row['l_media']}")
    #             span("]")
           
    #       else: # No best image
    #         with td(colspan=2):
    #           get_first_image_of = row['urn'].replace("urn:p-lod:id:","")
    #           palp_depicted_by_images(plodlib.PLODResource(get_first_image_of), first_only = True)


  return element



# type renderers
def city_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):
      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="depicts_concepts",style="width:80%"):
        span("Depicts the Concepts: ")
        palp_depicts_concepts(r)
      
      with div(id="spatial_children", style="width:80%"):
        span("Insula and Streets Within: ")
        palp_spatial_children(r, images = False)



def region_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):

      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="spatial_hierarchy", style="margin-bottom:.5em, width:80%"):
        palp_spatial_hierarchy(r)

      with div(id="depicts_concepts: ", style="width:80%"):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)

      with div(id="spatial_children", style="width:80%"):
        span("Insula and Streets Within: ")
        palp_spatial_children(r)


def insula_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):

      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="spatial_hierarchy", style="margin-bottom:1em, width:80%"):
        palp_spatial_hierarchy(r)
        
      with div(id="depicts_concepts: ", style="width:80%"):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)

      # with div(id="images"):
      #   palp_image_gallery(r)
      #   div(id = 'galleria-display', style="width:80%")

      with div(id="spatial_children", style="width:80%"):
        span("Properties Within: ")
        palp_spatial_children(r)

      
    # galleria_inline_script()


def property_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):

      eng_titles =  r.get_predicate_values('urn:p-lod:id:plod-english-title')
      it_titles  =  r.get_predicate_values('urn:p-lod:id:plod-italian-title')

      known_as = " / ".join(json.loads(eng_titles) + json.loads(it_titles))

      if known_as:
        with div("Other name(s): ", style="margin-bottom:1em, width:80%"):
          span(known_as)

      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="spatial_hierarchy", style="margin-bottom:1em, width:80%"):
        palp_spatial_hierarchy(r)

      with div(id="depicts_concepts: ", style="width:80%"):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)

      with div(id="images"):
        palp_image_gallery(r)
        div(id = 'galleria-display', style="width:80%")

      with div(id="spatial_children", style="width:80%"):
        span("Spaces (aka 'Rooms') Within: ")
        palp_spatial_children(r, images = False)


    galleria_inline_script()


def space_render(r,html_dom):

  with html_dom:
    with main(cls="container", role="main"):

      if r.geojson:
        with div(id="geojson"):
          palp_geojson(r)

      with div(id="spatial_hierarchy", style="margin-bottom:1em, width:80%"):
        palp_spatial_hierarchy(r)

      with div(id="depicts_concepts: ", style="width:80%"):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)

      with div(id="images", style="margin-top:6px"):
        palp_image_gallery(r)
        div(id = 'galleria-display', style="width:80%")

      with div(id="spatial_children", style="margin-top:6px, width:80%"):
        span("It contains features: ")
        palp_spatial_children(r, images = False)

    galleria_inline_script()

def feature_render(r,html_dom):
  
  with html_dom:
    with main(cls="container", role="main"):

      if r.geojson or json.loads(r.spatially_within):
          with div(id="geojson", style="margin-top:6px"):
            palp_geojson(r)

      with div(id="spatial_hierarchy", style="margin-bottom:1em"):
        palp_spatial_hierarchy(r)

      
      with div(id="depicts_concepts", style="margin-top:6px, width:80%"):
        span("Depicts Concepts: ")
        palp_depicts_concepts(r)

      with div(id="images", style="margin-top:10px"):
        palp_image_gallery(r)
        div(id = 'galleria-display', style="width:80%")
      
    galleria_inline_script()
    

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
        with div(id="geojson", style="margin-top:12px"):
          palp_geojson(r)


      
      with div(id="images", style="margin-top:8px"):
        with div(style="width:80%"):
          i(f"Note: For the time being, PALP may include images below that do not directly show '{r.identifier}'. This can be because those images show details or distant overviews of a wall-painting or other artwork that does. The selection of images will become more precise and relevant as development and data-entry continue.", style="width:80%")
        palp_image_gallery(r)
        div(id = 'galleria-display', style="width:80%; margin-top:2px")
        hr()

      with div(id="depicted-where", style="margin-top:3px; width:80%"):
        b(r.identifier)
        span(" is depicted in the following rooms or spaces: ")
        palp_depicted_where(r, level_of_detail='space')
        hr()

      with div(id="full-text-search", style="margin-top:3px; width:80%"):
        span("Keyword search for “")
        a(r.identifier, href=f"/full-text-search?q={r.identifier}")
        span("”.")

    galleria_inline_script()
          


def street_render(r,html_dom):

  with html_dom:

    if r.geojson:
      with div(id="geojson"):
        r.geojson[0:20]

    with div(id="spatial_hierarchy", style="margin-bottom:1em"):
      palp_spatial_hierarchy(r)


def luna_image_render(r,html_dom):
  with html_dom:
    with main(cls="container", role="main"):
      span(r.identifier)
    
    try:
      t_val = luna_tilde_val(f'urn:p-lod:id:{r.identifier}')
      media_id = json.loads(r.get_predicate_values('urn:p-lod:id:x-luna-media-id'))[0]
      record_id = json.loads(r.get_predicate_values('urn:p-lod:id:x-luna-record-id'))[0]
      
      html_df = r._id_df.copy()
      
      try:
        depicts_urn = html_df.loc['urn:p-lod:id:depicts','o']

        r_depicted = plodlib.PLODResource(depicts_urn.replace('urn:p-lod:id:',''))
        r_depicted_is_within = plodlib.PLODResource(json.loads(r_depicted.spatially_within)[0]['urn'].replace('urn:p-lod:id:',''))
      
        #html_df.loc['urn:p-lod:id:depicts','o'] = f'<a href="/browse/{r._id_df.loc["urn:p-lod:id:depicts","o"].replace("urn:p-lod:id:","")}">{r._id_df.loc["urn:p-lod:id:depicts","o"]}</a>'
        #html_df.loc['urn:p-lod:id:depicts','o'] = f'<a href="/browse/{r_depicted}">{r_depicted}</a> within <a href="/browse/{r_depicted_within}">{r_depicted_within}"</a>'
        html_df.loc['urn:p-lod:id:depicts','o'] = f'<a href="/browse/{r_depicted.identifier}">{r_depicted.identifier}</a> within <a href="/browse/{r_depicted_is_within.identifier}">{r_depicted_is_within.identifier}</a>'
      except:
        div("ERROR")


      raw(html_df.to_html(escape = False, header = False))
      
      raw(f'''
      <iframe allowfullscreen="true" id="widgetPreview" frameBorder="0"  width="100%"  height="350px"  border="0px" style="border:0px solid white"  src="http://umassamherst.lunaimaging.com/luna/servlet/detail/umass~{t_val}~{t_val}~{record_id}~{media_id}?widgetFormat=javascript&widgetType=detail&controls=1&nsip=1" ></iframe>
      ''')

      with div():
        a("View in Luna (from UMass Amherst Library)",href=f"https://umassamherst.lunaimaging.com/luna/servlet/detail/umass~{t_val}~{t_val}~{record_id}~{media_id}", target="_new")

    


    except:
      1


    

      


def unknown_render(r,html_dom):

  with html_dom:
    span(f"{r.identifier} Unknown type.")



def palp_html_document(r = POMPEII,renderer = None):

  
  html_dom = dominate.document(title=f"Pompeii Artistic Landscape Project: {r.identifier}" )

  palp_html_head(r, html_dom)
  html_dom.body
  palp_page_navbar(r,html_dom)

  if r:
    renderer(r, html_dom)

  palp_page_footer(r, html_dom)

  return html_dom


# The PALP Verbs that Enable Navigation

@app.route('/browse/<path:identifier>')
def palp_browse(identifier):

  r = plodlib.PLODResource(identifier)

  try:
    return palp_html_document(r, globals()[f'{r.rdf_type.replace("-","_")}_render']).render() # call p_h_d with right render function if it exists
  except KeyError as e:
    return palp_html_document(r,unknown_render).render()

@app.route('/map/')
def palp_map():
    return """Super cool and useful map page. What should it do? <a href="/start">Start</a>."""

@app.route('/search/')
def palp_search():
    return """Super cool and useful search page. What should it do? <a href="/start">Start</a>."""

@app.route('/compare/')
def palp_compare():
    return """Super cool and useful search page. What should it do? <a href="/start">Start</a>. """

@app.route('/')
def index():
    return redirect("/start", code=302)

@app.route('/geojson/<path:identifier>')
def web_api_geojson(identifier):
  return plodlib.PLODResource(identifier).geojson

@app.route('/images/<path:identifier>')
def web_api_images(identifier):
  return plodlib.PLODResource(identifier).gather_images()

@app.route('/start')
def palp_start():
  r = plodlib.PLODResource("Pompeii")
  html_dom = dominate.document(title=f"Pompeii Artistic Landscape Project" )

  palp_html_head(r, html_dom)
  html_dom.body
  palp_page_navbar(r,html_dom)

  with html_dom:
    with main(cls="container", role="main"):
      with div(id="page-content-wrapper"):
        with div(id="container-fluid"):
          with p():
            b("Please note that this website, its data, and interface are all under construction.")
          p(raw("""The <b>Pompeii Artistic Landscape Project</b> (PALP) is an online resource that supports sitewide discovery, mapping, analysis, and sharing of information about Pompeian artworks in their architectural and urban contexts. The goal of PALP is to dramatically increase the number of researchers and members of the public who can access, analyze, interpret, and share the artworks of the most richly documented urban environment of the Roman world: Pompeii."""), style="margin-top:1em")
          with p():
            span("Start browsing at ")
            a("http://palp.art/browse/pompeii",href="/browse/pompeii")
            span(" or ")
            a("http://palp.art/browse/sphinx",href="/browse/sphinx")
            span(".")
          p(raw("""Browsing within PALP will usually show location(s) and images related to the identifier being viewed. PALP has assigned identifiers to thousands of images, rooms, and properties at Pompeii, as well as to regions, insulae, and the city itself. It has also assigned identifiers to concepts that appear in Pompeian wall paintings, such as ”<a href="/browse/dog">dog</a>”. Browsing to ‘pompeii’ will show all concepts identified to date. In general, PALP uses short web-address (URLs) that are easy to remember and that can be easily shared."""))
          p(raw("""PALP is a collaborative initiative between <a href="https://www.umass.edu/classics/member/eric-poehler">Eric Poehler</a> at the University of Massachusetts Amherst and <a href="https://isaw.nyu.edu/people/faculty/sebastian-heath">Sebastian Heath</a> at the Institute for the Study of the Ancient World at New York University. It builds on data from the <a href="https://digitalhumanities.umass.edu/pbmp/">Pompeii Bibliography and Mapping Project</a> and uses other public resources such as <a href="http://pompeiiinpictures.com">Pompeii in Pictures</a>. It is developed using open source software and is informed by Linked Open Data approaches to sharing information. PALP is generously funded through a grant from the <a href="https://www.getty.edu/foundation/">Getty Foundation</a>, as part of its <a href="https://www.getty.edu/foundation/initiatives/current/dah/index.html">Digital Art History</a> initiative</a>. The <a href="https://palp.p-lod.umasscreate.net">project blog</a> has more information about PALP's scope and goals."""))
          with div(style="text-align:center"):
            with a(href="/browse/magpie"):
              img(src="http://umassamherst.lunaimaging.com/MediaManager/srvr?mediafile=/Size2/umass~14~14/4219/image34143.jpg", style="width:125px")
            with a(href="https://www.umass.edu"):
              img(src="static/images/umass-logo.png", style="max-width:200px")
            with a(href="https://www.getty.edu/foundation/"):
              img(src="static/images/getty-logo.jpg", style="max-width:220px")
            with a(href="https://isaw.nyu.edu"):
              img(src="static/images/nyu-logo.png", style="max-width:200px")
            

  palp_page_footer(r, html_dom)
  return html_dom.render()

@app.route('/full-text-search')
def fulltextsearch():

  html_dom = dominate.document(title="Pompeii Artistic Landscape Project: Keyword Search" )
  palp_html_head(POMPEII, html_dom)
  html_dom.body
  palp_page_navbar(POMPEII,html_dom)

  q = request.args.get('q')

  if q != '' and q is not None:

    q = q.lower().replace(' and ',' AND ')

    store = SPARQLStore(query_endpoint = "http://52.170.134.25:3030/plod_endpoint/query",
                                        context_aware = False,
                                        returnFormat = 'json')
    
    g_ft = rdf.Graph(store)

    qt = Template("""
    PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX text:  <http://jena.apache.org/text#>
    PREFIX p-lod: <urn:p-lod:id:>

    SELECT DISTINCT ?s ?type ?slabel ?d
    WHERE { 

    # ?s p-lod:description ?d .
      ?s text:query (rdfs:label p-lod:description p-lod:x-luna-description '$ft_query') ;
          rdfs:label ?slabel ; 
          a ?type .
      OPTIONAL { ?s p-lod:description|p-lod:x-luna-description ?d }.
    }
    """)  


    ftresults = g_ft.query(qt.substitute(ft_query = q))

    df = pd.DataFrame(ftresults, columns = ftresults.json['head']['vars'])
    df = df.applymap(str)
    # df.set_index('s', inplace = True)

    df['s'] = df['s'].apply(lambda x: f'<a href="browse/{x.replace("urn:p-lod:id:","")}">Browse</a>')
    df['type'] = df['type'].apply(lambda x: x.replace("urn:p-lod:id:",""))
    df.index += 1

    with html_dom:
      with main(cls="container", role="main"):
        div(f'Searched for: "{py_html.escape(q)}"', style='padding-bottom: .5em')
        
        raw(df.to_html(escape=False, header=False))

  palp_page_footer(POMPEII, html_dom)

  return html_dom.render()
      


 

import os
import html
from rdflib import Graph, Namespace, URIRef
from collections import defaultdict

class ISWC2019:
    def __init__(self,ruta):
        # Inicializar grafo y ontologías
        self.ruta = ruta
        self.grafo = Graph()
        self.ontologias = {
            'conf': Namespace("https://w3id.org/scholarlydata/ontology/conferenceontology.owl#"),
            'dbo': Namespace("http://dbpedia.org/ontology/"),
            'dbp': Namespace("http://dbpedia.org/property/"),
            'rdfs': Namespace("http://www.w3.org/2000/01/rdf-schema#")
        }
        for prefijo, ns in self.ontologias.items():
            self.grafo.bind(prefijo, ns)
        self.cache_autores = {}

    def cargar_archivos(self):
        # Cargar archivos TTL
        archivos_ttl = [
            "Datos_conferencia_iswc-2019.ttl",
            "Paises.ttl",
            "Paises_afiliacion_conferencia.ttl"
        ]
        for archivo in archivos_ttl:
            ruta = os.path.join(self.ruta, archivo)
            if os.path.exists(ruta):
                self.grafo.parse(ruta, format="turtle")
            else:
                print(f"⚠️ Archivo no encontrado: {ruta}")

    def obtener_nombre_autor(self, uri_autor):
        # Nombre de autor en caché
        if uri_autor not in self.cache_autores:
            nombre = self.grafo.value(subject=URIRef(uri_autor), predicate=self.ontologias['conf'].name)
            self.cache_autores[uri_autor] = str(nombre) if nombre else "Desconocido"
        return self.cache_autores[uri_autor]

    def obtener_autores_ordenados(self, uri_articulo):
        # Obtener autores ordenados
        lista_autores = self.grafo.value(subject=URIRef(uri_articulo), predicate=self.ontologias['conf'].hasAuthorList)
        if not lista_autores:
            return []
        autores = []
        nodo_actual = self.grafo.value(subject=lista_autores, predicate=self.ontologias['conf'].hasFirstItem)
        while nodo_actual:
            uri_autor = self.grafo.value(subject=nodo_actual, predicate=self.ontologias['conf'].hasContent)
            if uri_autor:
                autores.append(self.obtener_nombre_autor(uri_autor))
            nodo_actual = self.grafo.value(subject=nodo_actual, predicate=self.ontologias['conf'].next)
        return autores

    def formatear_autores(self, lista_autores):
        # Formato tipo APA
        if not lista_autores:
            return "Desconocido"
        if len(lista_autores) == 1:
            return lista_autores[0]
        if len(lista_autores) == 2:
            return f"{lista_autores[0]} y {lista_autores[1]}"
        return f"{', '.join(lista_autores[:-1])} y {lista_autores[-1]}"

    def consultar_publicaciones(self):
        # Consulta SPARQL
        consulta = """
        PREFIX conference: <https://w3id.org/scholarlydata/ontology/conference-ontology.owl#>
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbp: <http://dbpedia.org/property/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?paper ?title ?track ?countryName
        WHERE {
            ?p a conference:Track ;
               conference:hasSubEvent ?a ;
               rdfs:label ?track .
            ?a a conference:Talk ;
               conference:isEventRelatedTo ?paper .
            ?paper rdfs:label ?title ;
                   conference:hasAuthorList ?authorList .
            ?authorList conference:hasFirstItem ?item .
            ?item conference:hasContent ?author .
            ?affiliation a conference:AffiliationDuringEvent ;
                         conference:isAffiliationOf ?author ;
                         conference:withOrganisation ?organisation .
            ?organisation dbo:country ?country .
            ?country dbp:name ?countryName .
            FILTER (?track IN ("In-Use", "Research", "Resource"))
        }
        ORDER BY ?countryName ?title
        """
        return self.grafo.query(consulta)

    def generar_html(self, archivo_salida):
        # Generar HTML con estilo
        resultados = self.consultar_publicaciones()
        publicaciones_por_pais = defaultdict(set)
        info_articulos = {}
        etiquetas_tracks = {"Research": "(IN)", "In-Use": "(EU)", "Resource": "(RC)"}

        for fila in resultados:
            uri = str(fila.paper)
            titulo = str(fila.title)
            track = str(fila.track)
            pais = str(fila.countryName)
            etiqueta = etiquetas_tracks.get(track, "")
            autores = self.formatear_autores(self.obtener_autores_ordenados(uri))
            clave_articulo = (uri, titulo)
            info_articulos[clave_articulo] = (etiqueta, titulo, autores)
            publicaciones_por_pais[pais].add(clave_articulo)

        html_lineas = [
            "<!DOCTYPE html>",
            "<html lang='es'>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<title>Publicaciones ISWC 2019</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f9; }",
            "h1 { color: #2c3e50; }",
            "h2 { color: #34495e; border-bottom: 1px solid #ccc; padding-bottom: 5px; }",
            "p { margin-left: 20px; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Publicaciones ISWC 2019 por País</h1>",
            "<p>Tracks: Investigación, En uso y Recursos.</p>"
        ]

        for pais in sorted(publicaciones_por_pais.keys()):
            html_lineas.append(f"<h2>{html.escape(pais)}</h2>")
            articulos = sorted(publicaciones_por_pais[pais], key=lambda x: x[1])
            for clave in articulos:
                etiqueta, titulo, autores = info_articulos[clave]
                html_lineas.append(f"<p>{etiqueta} \"{html.escape(titulo)}\" por {html.escape(autores)}</p>")

        html_lineas.extend(["</body>", "</html>"])

        with open(archivo_salida, "w", encoding="utf-8") as f:
            f.write("\n".join(html_lineas))

    def run(self):
        # Ejecutar todo
        self.cargar_archivos()
        self.generar_html(archivo_salida="Publicaciones2019.html")
        print(f"✅ HTML generado en: {os.path.abspath('Publicaciones2019.html')}")

if __name__ == "__main__":
    ruta = "Datos"
    resumen = ISWC2019(ruta)
    resumen.run()

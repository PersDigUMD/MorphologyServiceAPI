'''
Created on Nov 7, 2015

@author: elijah Cooke
'''
from __future__ import unicode_literals
from flask import Flask,abort, jsonify, json
from flask_restful import Resource, Api, reqparse
from hazm import POSTagger,word_tokenize, sent_tokenize
from hazm.Stemmer import Stemmer
from hazm.Lemmatizer import Lemmatizer
from hazm.Normalizer import Normalizer
import urllib
import uuid

try:
    from lxml import etree
    print("running with lxml.etree")
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
        print("running with cElementTree on Python 2.5+")
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
            print("running with ElementTree on Python 2.5+")
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
                print("running with cElementTree")
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                    print("running with ElementTree")
                except ImportError:
                    print("Failed to import ElementTree from any known place")

app = Flask(__name__)
api = Api(app)

def toalpheiosxml(analysis):
    root = etree.Element('words')
    for item in analysis:
        word = etree.SubElement(root,'word')
        form = etree.SubElement(word, 'form', {'{http://www.w3.org/XML/1998/namespace}lang': item['form']['lang']})
        form.text = item['form']['text']
        for entry in item['entries']:
            word.append(entrytoxml(entry))
    return root

def entrytoxml(entry):
    root = etree.Element('entry')
    dic = etree.SubElement(root,'dict')
    hdwd = etree.SubElement(dic,'hdwd', {'{http://www.w3.org/XML/1998/namespace}lang':entry['dict']['hdwd']['lang']})
    hdwd.text = entry['dict']['hdwd']['text']
    for i in entry['infls']:
      infl = etree.SubElement(root,'infl')
      term = etree.SubElement(infl, 'term', {'{http://www.w3.org/XML/1998/namespace}lang':i['stem']['lang']})
      stem = etree.SubElement(term, 'stem')
      stem.text = i['stem']['text']
      if i['pofs']['text']:
        pofs = etree.SubElement(infl, 'pofs', {'order':i['pofs']['order']})
        pofs.text = i['pofs']['text']
    return root

def tobspmorph(analysis):
    root = etree.Element("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF")    
    for word in analysis:
        annotation_id = 'urn:TuftsMorphologyService:'+word['form']['text'] + ':' + word['engine']
        oaannotation = etree.SubElement(root,'{http://www.w3.org/ns/oa#}Annotation',{'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about': annotation_id})
        oahastarget = etree.SubElement(oaannotation,'{http://www.w3.org/ns/oa#}hasTarget')
        desc = etree.SubElement(oahastarget,'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description',{'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about':word['uri']})
        title = etree.SubElement(oaannotation, '{http://purl.org/dc/elements/1.1/}title', {'{http://www.w3.org/XML/1998/namespace}lang':'eng'})
        title.text = "Morphology of " + word['form']['text']
        for entry in word['entries']:
            entry_id = str(uuid.uuid1().urn)
            oahasbody = etree.SubElement(oaannotation, '{http://www.w3.org/ns/oa#}hasBody',{'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource':entry_id})
            oabody = etree.SubElement(oaannotation, '{http://www.w3.org/ns/oa#}Body',{'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource':entry_id})
            bodytype = etree.SubElement(oabody, '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}type',{'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource':'http://www.w3.org/2008/content#ContentAsXML'})
            content = etree.SubElement(oabody, '{http://www.w3.org/2008/content#}rest')
            content.append(entrytoxml(entry))
    return root

#def analysistojson

def hazmtoalpheios(word,uri):
    wordslist = etree.Element("words")
    normalizer = Normalizer()
    data = normalizer.normalize(word)
    sentences = sent_tokenize(data)
    words = []
    for sentence in sentences:
        if words:
            words = words.append(word_tokenize(sentence))
        else:
            words = word_tokenize(sentence)
    analyses = []
    for item in words:
        stemmer = Stemmer()
        wordstem = stemmer.stem(item)
        lemmatizer = Lemmatizer()
        wordlema = lemmatizer.lemmatize(item)
        if '#' in wordlema:
            worldleam, garbage = wordlema.split("#")
        tagger = POSTagger(model="postagger.model")
        wordtagged = tagger.tag(item)
        wordpofs = wordtagged[0][1]
        wordpofs = maptohazm(wordpofs)
        analysis = {}
        analysis['engine'] = 'hazm'
        analysis['uri'] = uri
        analysis['form'] = {}
        analysis['form']['text'] = item
        analysis['form']['lang'] = 'per'
        analysis['entries'] = []
        entry = {}
        entry['dict'] = {}
        entry['dict']['hdwd'] = {}
        entry['dict']['hdwd']['lang'] = 'per'
        entry['dict']['hdwd']['text'] = wordstem
        entry['infls'] = []
        infl = {}
        infl['stem'] = {} 
        infl['stem']['text'] = wordstem
        infl['stem']['lang'] = 'per'
        infl['pofs'] = {}
        if wordpofs:
            infl['pofs']['order'] = str(wordpofs[1])
            infl['pofs']['text'] = wordpofs[0]
        entry['infls'].append(infl)
        analysis['entries'].append(entry)
        analyses.append(analysis)
    return analyses

def maptohazm(wordpofs):
    if wordpofs == "N":
        wordpofs = ["noun",1]
        return wordpofs
    if wordpofs == "INT":
        wordpofs = ["Interjection",2]
        return wordpofs
    if wordpofs == "DET":
        wordpofs = ["Determiner",3]
        return wordpofs
    if wordpofs == "AJ":
        wordpofs = ["Adjective",4]
        return wordpofs
    if wordpofs == "P":
        wordpofs = ["Preposition",5]
        return wordpofs
    if wordpofs == "PRO":
        wordpofs = ["Pronoun",6]
        return wordpofs
    if wordpofs == "CONJ":
        wordpofs = ["Conjunction",7]
        return wordpofs
    if wordpofs == "V":
        wordpofs = ["Verb",8]
        return wordpofs
    if wordpofs == "ADV":
        wordpofs = ["Adverb",9]
        return wordpofs
    if wordpofs == "POSTP":
        wordpofs = ["Postposition",10]
        return wordpofs
    if wordpofs == "Num":
        wordpofs = ["Number",11]
        return wordpofs
    if wordpofs == "CL":
        wordpofs = ["Classifier",12]
        return wordpofs
    if wordpofs == "e":
        wordpofs = ["ezafe",13]
        return wordpofs
def hazmtoalpheiosfile(data,uri):
    root = etree.Element("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF")    
    oaannotation = etree.SubElement(root,'{http://www.w3.org/ns/oa#}Annotation',{'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about':'http://services.projectbamboo.org/morphology'+uri})
    oahasbody = etree.SubElement(oaannotation, '{http://www.w3.org/ns/oa#}hasBody',)
    oahastarget = etree.SubElement(oaannotation,'{http://www.w3.org/ns/oa#}hasTarget')
    hasbodydesc = etree.SubElement(oahastarget,'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description',{'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about':uri})
    ispartof = etree.SubElement(hasbodydesc,'{http://purl.org/dc/terms/}isPartOf',{'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about':uri})
    source = etree.SubElement(hasbodydesc,'{http://purl.org/dc/terms/}source',{'{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource':uri})
    title = etree.SubElement(oaannotation, '{http://purl.org/dc/elements/1.1/}title', {'{http://www.w3.org/XML/1998/namespace}lang':'eng'})
    title.text = "Morphology of " + uri
    wordslist = etree.SubElement("words")
    normalizer = Normalizer()
    data = normalizer.normalize(data)
    sentences = sent_tokenize(data)
    words = []
    for sentence in sentences:
        if words:
            words = words.append(word_tokenize(sentence))
        else:
            words = word_tokenize(sentence)
    for item in words:
        stemmer = Stemmer()
        wordstem = stemmer.stem(item)
        lemmatizer = Lemmatizer()
        wordlema = lemmatizer.lemmatize(item)
        if '#' in wordlema:
            worldleam, garbage = wordlema.split("#")
        tagger = POSTagger(model="postagger.model")
        wordtagged = tagger.tag(item)
        wordpofs = wordtagged[0][1]
        word = etree.SubElement(wordslist,'word')
        form = etree.SubElement(word, 'form', {'{http://www.w3.org/XML/1998/namespace}lang':'per'})
        form.text = item
        entry = etree.SubElement(word, 'entry')
        infl = etree.SubElement(entry,'inlf')
        term = etree.SubElement(infl, 'term', {'{http://www.w3.org/XML/1998/namespace}lang':'per'})
        stem = etree.SubElement(term, 'stem')
        stem.text = wordstem
        pofs = etree.SubElement(infl, 'pofs')
        pofs.text = wordpofs
    return root

def casltoalphioes():
    pass
        
class EngineListAPI(Resource):
    def get(self):
        root = etree.Element("EngineListXMLRepresentation")
        ouput = etree.ElementTree(root)
        listmeta = etree.SubElement(root, "listMetadata", {'type':'bsp:listMetadataType'})
        listentries = etree.SubElement(root, "listEntries")
        engineone = etree.SubElement(listentries, "listEntry", {"type":"EngineListEntry", 'maxOccurs':"unbounded",'minOccours':'1'})
        terms1 = etree.SubElement(engineone, "description")
        slcode1 = etree.SubElement(engineone, "supportsLanguageCode", {'type':'xs:string', 'maxOccurs':'unbounded', 'minOccours':'1'})
        supopt1 = etree.SubElement(engineone, "supportsOption", {'type':'xs:string','maxOccurs':'unbounded','minOccurs':'1'})
        enginetwo = etree.SubElement(listentries, "listEntry", {"type":"EngineListEntry", 'maxOccurs':"unbounded",'minOccours':'1'})
        terms2 = etree.SubElement(enginetwo, "description")
        slcode2 = etree.SubElement(enginetwo, "supportsLanguageCode", {'type':'xs:string', 'maxOccurs':'unbounded', 'minOccours':'1'})
        supopt2 = etree.SubElement(enginetwo, "supportsOption", {'type':'xs:string','maxOccurs':'unbounded','minOccurs':'1'})
        return root

class EngineAPI(Resource):
    def get(self, id):
        if id == "hazm":
            root = etree.Element("EngineListXMLRepresentation")
            ouput = etree.ElementTree(root)
            listmeta = etree.SubElement(root, "listMetadata", {'type':'bsp:listMetadataType'})
            listentries = etree.SubElement(root, "listEntries")
            engine = etree.SubElement(listentries, "listEntry", {"type":"EngineListEntry", 'maxOccurs':"unbounded",'minOccours':'1'})
            terms = etree.SubElement(engine, "description")
            slcode = etree.SubElement(engine, "supportsLanguageCode", {'type':'xs:string', 'maxOccurs':'unbounded', 'minOccours':'1'})
            supopt = etree.SubElement(engine, "supportsOption", {'type':'xs:string','maxOccurs':'unbounded','minOccurs':'1'})
        if id == "casl":
            root = etree.Element("EngineListXMLRepresentation")
            ouput = etree.ElementTree(root)
            listmeta = etree.SubElement(root, "listMetadata", {'type':'bsp:listMetadataType'})
            listentries = etree.SubElement(root, "listEntries")
            engine = etree.SubElement(listentries, "listEntry", {"type":"EngineListEntry", 'maxOccurs':"unbounded",'minOccours':'1'})
            terms = etree.SubElement(engine, "description")
            slcode = etree.SubElement(engine, "supportsLanguageCode", {'type':'xs:string', 'maxOccurs':'unbounded', 'minOccours':'1'})
            supopt = etree.SubElement(engine, "supportsOption", {'type':'xs:string','maxOccurs':'unbounded','minOccurs':'1'})
        if root:
            return root
        else:
            abort(404)

'''    
class RepoListAPI(Resource):
    def get(self):
        pass
    
class RepoAPI(Resource):
    def get(self, id):
        pass
'''

'''
Responds to a Alpheios Legacy API Request
'''        
class AlpheiosWordList(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('word')
        args = parser.parse_args()
        word = args['word']
        word_uri = 'urn:word:'+word
        analysis = hazmtoalpheios(word,word_uri)
        tree = toalpheiosxml(analysis)
        return tree
 
'''
Responds to Request for analysis of a single word
'''        
class AnalysisWord(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('engine')
        parser.add_argument('lang')
        parser.add_argument('word')
        parser.add_argument('word_uri', required = False, type = str, location = 'HTTP')
        args = parser.parse_args()
        lang = args['lang']
        engine = args['engine']
        word = args['word']
        word_uri = args["word_uri"]
        if not word_uri:
            word_uri = 'urn:word:'+word
        if lang != 'per':
            return {"error":"unsupported language"},404
        if engine == "hazm":
            analysis = hazmtoalpheios(word,word_uri)
            tree = tobspmorph(analysis)
            return tree,201
        else:
            return {"error":"unknown engine"},404
            
    
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('engine')
        parser.add_argument('lang')
        parser.add_argument('word')
        parser.add_argument('word_uri', required = False, type = str, location = 'HTTP')
        args = parser.parse_args()
        lang = args['lang']
        engine = args['engine']
        word = args['word']
        word_uri = args['word_uri']
        if not word_uri:
            word_uri = 'urn:word:'+word
        if lang != 'per':
            return {"error":"unsupported language"},404
        if engine == "hazm":
            analysis = hazmtoalpheios(word,word_uri)
            tree = tobspmorph(analysis)
            return tree,201
        else:
            return {"error":"unknown engine"},404
    
class AnalysisDoc(Resource):
    def get(self, doc):
        parser = reqparse.RequestParser()
        parser.add_argument('document_id', required = True, type=str, location = 'HTTP')
        parser.add_argument('engine', required = True, type = str, location = 'HTTP')
        parser.add_argument('lang', required = True, type = str, location = 'HTTP')
        parser.add_argument('wait', required = False, type = str, location = 'HTTP')
        args = parser.parse_args()
        doc_id = args['document_id']
        engine = args['engine']
        lang = args['lang']
        doc = urllib.request.urlopen(doc_id)
        if lang != 'per':
            return {'error':'unsupported engine'},404
        if engine == 'hazm':
            analysis = hazmtoalpheios(doc)
            tree = tobspmorph(analysis)
            return etree,201
        
    def post(self, doc):
        parser = reqparse.RequestParser()
        parser.add_argument('document_id', required = True, type=str, location = 'HTTP')
        parser.add_argument('engine', required = True, type = str, location = 'HTTP')
        parser.add_argument('lang', required = True, type = str, location = 'HTTP')
        parser.add_argument('wait', required = False, type = str, location = 'HTTP')
        args = parser.parse_args()
        doc_id = args['document_id']
        engine = args['engine']
        lang = args['lang']
        wait = args['wait']
        doc = urllib.request.urlopen(doc_id)
        if lang != 'per':
            return {'error':'unsupported engine'},404
        if wait == True:
            if engine == 'hazm':
                analysis = hazmtoalpheios(doc)
                tree = tobspmorph(analysis)
                return tree,201
            
class AnalysisText(Resource):
    def get(self, text):
        parser = reqparse.RequestParser()
        parser.add_argument('mime_type')
        parser.add_argument('lang')
        parser.add_argument('engine', required = False)
        parser.add_argument('text_uri', required = False, type = str, location = 'HTTP')
        parser.add_argument('text', required = False, type = str, location = 'HTTP')        
        args = parser.parse_args()
        lang = args['lang']
        engine = args['engine']
        mime_type = args['mime_type']
        text = args['text']
        text_uri = ["text_uri"]
        if not engine:
            engine = 'hazm'
        if not text_uri or text:
            return "error, must supply either a text or a text URI",400
        if not text_uri:
            text_uri = "unknown text"
        if not text:
            text = urllib.request.urlopen(text_uri)
        if lang != 'per':
            return {"error":"unsupported language"},404
        if mime_type == 'text/plain':           
            if engine == "hazm":
                analysis = hazmtoalpheios(text,text_uri)
                tree = tobspmorph(analysis)
                return tree,201
            else:
                return {"error":"unknown engine"},404
        else:
            if mime_type == 'text/html':
                return {"error":"unsupported Mime_type"},415
            else:
                if mime_type == 'text/xml':
                    return {'error':'unsupported Mime_type'},415
                else:
                    return {'error':'unsupported Mime_type'},415
    
    def post(self, text):
        parser = reqparse.RequestParser()
        parser.add_argument('mime_type')
        parser.add_argument('lang')
        parser.add_argument('engine', required = False)
        parser.add_argument('text_uri', required = False, type = str, location = 'HTTP')
        parser.add_argument('text', required = False, type = str, location = 'HTTP')        
        args = parser.parse_args()
        lang = args['lang']
        engine = args['engine']
        mime_type = args['mime_type']
        text = args['text']
        text_uri = ["text_uri"]
        if not engine:
            engine = 'hazm'
        if not text_uri or text:
            return "error, must supply either a text or a text URI",400
        if not text_uri:
            text_uri = "unknown text"
        if not text:
            text = urllib.request.urlopen(text_uri)
        if lang != 'per':
            return {"error":"unsupported language"},404
        if mime_type == 'text/plain':           
            if engine == "hazm":
                analysis = hazmtoalpheios(text,text_uri)
                tree = tobspmorph(analysis)
                return tree,201
            else:
                return {"error":"unknown engine"},404
        else:
            if mime_type == 'text/html':
                return {"error":"unsupported Mime_type"},415
            else:
                if mime_type == 'text/xml':
                    return {'error':'unsupported Mime_type'},415
                else:
                    return {'error':'unsupported Mime_type'},415

    @api.representation('application/xml')
    def output_xml(data, code, headers=None):
        resp = app.make_response(etree.tostring(data, pretty_print=True, xml_declaration=True, encoding='utf-8').decode())
        resp.headers.extend(headers or {})
        return resp
    
    def _init_(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('mime_type', required = True, type=str, location = 'HTTP')
        self.reqparse.add_argument('text', required = False, type=str, location = 'HTTP')
        self.reqparse.add_argument('text_uri', required = False, type=str, location = 'HTTP')
        self.reqparse.add_argument('engine', required = True, type = str, location = 'HTTP')
        self.reqparse.add_argument('lang', required = True, type = str, location = 'HTTP')
        super(AnalysisWord, self).__init__()
    
api.add_resource(EngineListAPI, '/morphologyservice/engine')
api.add_resource(EngineAPI, '/morphologyservice/engine/<EngineId>')
#api.add_resource(RepoListAPI, '/morphologyservice/repository', endpoint = 'tasks')
#api.add_resource(RepoAPI, '/morphologyservice/repository/<RepoId>', endpoint = 'tasks')
api.add_resource(AnalysisWord, '/morphologyservice/analysis/word')
api.add_resource(AnalysisDoc, '/morphologyservice/analysis/document')
api.add_resource(AnalysisText, '/morphologyservice/analysis/text')

#this is the legacy Alpheios Service API
api.add_resource(AlpheiosWordList, '/alpheiosservice/hazm')


if __name__ == '__main__':
    app.run(debug=True)

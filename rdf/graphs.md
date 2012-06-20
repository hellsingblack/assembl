# On graphs and URLs

## Graphs granularity

How granular will graphs be? 
Here are layers of containment:

1. Server
2. Debate
3. DebatePhase
4. Viewpoint
5. ActiveDocument (incl. synthèse)
5. Thread
6. Item

(Note Thread and ActiveDocument are parallel.)
The sioc:embeds_knowledge property suggests each Item can have a Graph. That is very fine!
No question that each DebatePhase can have an underlying graph.
I maintain users can have private graphs (Viewpoint), plausibly maintained in a (set of) ActiveDocument, so ActiveDocument would be a minimum. Not sure Thread is meaningful, but open to it.

Either way, we need to search in (at least) a debate phase and find all relevant stuff. For that we need DB views, or a lot of sparql. Either way, it's a PITA because we need to tell librdf about the fact that the "reading" subgraph is not the same as the "writing" subgraph (while not being the whole DB either as in a conjunctive graph.)
In virtuoso, DB views are described [here](http://docs.openlinksw.com/virtuoso/rdfgraphsecurity.html).

## Possible URLs

Note: _xxx are literals, <> are placeholders for a tag. No tag can start with a _, naturally.

Those URLs all yield RDF. Most are graphs, marked by a *. Derived graphs are marked by #, and are generally a union of their subgraph.

	#http://server.domain.com/<server_prefix>/<debate>/
	#http://server.domain.com/<server_prefix>/<debate>/<phase>/
	*http://server.domain.com/<server_prefix>/<debate>/<phase>/_forum/
	http://server.domain.com/<server_prefix>/<debate>/<phase>/_forum/<postid>/
	http://server.domain.com/<server_prefix>/<debate>/<phase>/_concepts/
	http://server.domain.com/<server_prefix>/<debate>/<phase>/_concepts/<conceptid>
	http://server.domain.com/<server_prefix>/<debate>/<phase>/_concepts/<conceptid>/<expressionid>/
	*http://server.domain.com/<server_prefix>/<debate>/<phase>/_doc/<document_name>
	*http://server.domain.com/<server_prefix>/<debate>/<phase>/_doc/_synthese/
	http://server.domain.com/<server_prefix>/_users/
	http://server.domain.com/<server_prefix>/_users/<username>/
	*http://server.domain.com/<server_prefix>/_users/<username>/_doc/<document_name>
	*http://server.domain.com/<server_prefix>/_users/<username>/_doc/<document_name>/_snap/<snaphsot_name>


(do we need URLs for threads?)

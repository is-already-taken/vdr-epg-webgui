import cherrypy
import time
import sqlite3
import json
import os
import mimetypes
import re

DB = "/tmp/epg.sqlite3"

def handle_error():
    cherrypy.response.status = 500
    cherrypy.response.body = '{"code": 500}'


# Define own error class to respond with JSON always
#
class CustomError(cherrypy.HTTPError):

	def get_error_page(self, *args, **kwargs):
		return json.dumps({"code": self.code, "message": self.message})

# Disable this "feature"
#
cherrypy._cperror._ie_friendly_error_sizes = { }

class Search:
	exposed = True

	_cp_config = {'request.error_response': handle_error}

	def _build_query(self, d):
		# select * from programs p, channels c where c.rowid = p.channel_id and c.name like 'ARD-alpha' and p.title like '%deutsch%' order by p.start_time;
		q = "select c.name channel_name, p.title title, p.subtitle subtitle, p.description description, p.start_time start_time, p.duration duration from programs p, channels c where c.rowid = p.channel_id"
		p = []

		print "# Building query for " + str(d)

		if "title" in d:
			q += " and (p.title like ? or p.subtitle like ?)"
			p.append('%' +d["title"] + '%')
			p.append('%' +d["title"] + '%')

		if "description" in d:
			q += " and p.description like ?"
			p.append('%' +d["description"] + '%')

		if "channel_name" in d:
			q += " and c.name like ?"
			p.append('%' +d["channel_name"] + '%')

		if "time_lower" in d:
			q += " and p.start_time >= ?"
			p.append(d["time_lower"])

		if "time_upper" in d:
			q += " and p.start_time <= ?"
			p.append(d["time_upper"])

		print "# Built query: " + str(q) + ", ("+ str(p) +")"

		return (q, p)

	# def _query(self, title=None, description=None, channel_name=None, time_lower=None, time_upper=None):
	def _query(self, query):
		db_conn = sqlite3.connect(DB)
		db_conn.row_factory = sqlite3.Row

		cur = db_conn.cursor()

		# (query, params) = self._build_query({
		# 	"title": title,
		# 	"description": description,
		# 	"channel_name": channel_name,
		# 	"time_lower": time_lower,
		# 	"time_upper": time_upper
		# })

		(sql, params) = self._build_query(query)

		query = cur.execute(sql, params)
		rows = query.fetchall()

		data = []

		for row in rows:
			data.append({
				"title": str(row["title"]),
				"description": str(row["description"]),
				"subtitle": str(row["subtitle"]),
				"channel_name": str(row["channel_name"]),
				"start_time": str(row["start_time"]),
				"duration": str(row["duration"])
			})



		cur.close()
		db_conn.close()

		return data

	@cherrypy.tools.json_out()
	def POST(self, *args, **kwargs):
		params = cherrypy.request.body.params

		print "Query: " + params["query"]

		query = json.loads(params["query"])

		data =  self._query(query)

		print data

		return data

if __name__ == '__main__':


	config = {
		'/': {
			'tools.staticdir.on': True,
			'tools.staticdir.dir': os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
		},
		'/search': {
			'request.dispatch': cherrypy.dispatch.MethodDispatcher()
		}
	}

	cherrypy.tree.mount(Search(), config=config)

	cherrypy.config.update({
		'server.socket_host': '127.0.0.1',
		'server.socket_port': 8056
	})

	cherrypy.engine.start()
	cherrypy.engine.block()


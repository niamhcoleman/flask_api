import MySQLdb
from flask import Flask, jsonify, request
from datetime import datetime
from flask_cors import CORS, cross_origin
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config["DEBUG"] = True

db = MySQLdb.connect("niamhcoleman0.mysql.pythonanywhere-services.com", "niamhcoleman0", "securityiskey", "niamhcoleman0$fyp")

#return user email (account tab)
@app.route('/account/getuserinfo/<user_id>', methods=['GET'])
@cross_origin()
def getuserinfo(user_id):
    query = "SELECT user_name, user_email FROM niamhcoleman0$fyp.users WHERE user_id = %s;"
    cursor = db.cursor()
    cursor.execute(query % user_id)
    result = []
    for (user_name, user_email) in cursor:
        result.append({"user_name": user_name, "user_email": user_email})
    cursor.close()
    return jsonify(result)

#change user password
@app.route('/account/changepassword/<new_password>/<user_id>', methods=['POST'])
@cross_origin()
def changepassword(new_password,user_id):
    query = "UPDATE users SET user_password = %s WHERE user_id = %s;"
    cursor = db.cursor()
    cursor.execute(query % (new_password, user_id))
    db.commit()
    cursor.close()
    return "{'status': 'success'}"

#tracking symptoms
@app.route('/tracking/logentry', methods = ['POST'])
@cross_origin()
def logentry():
	try:
		cursor = db.cursor()
		user_id = request.args["user_id"]
		now = datetime.now()
		formatted_date = now.strftime('%Y-%m-%d')
		entry_tod = request.args["entry_tod"]
		entry_emo_id = request.args["entry_emo_id"]
		notes = request.args["notes"]
		symptoms = request.args.getlist('symptoms')

		query = "SELECT entry_id FROM entries WHERE user_id = '%s' AND entry_date = '%s' AND entry_tod = '%s';"
		cursor.execute(query  % (user_id, formatted_date, entry_tod))
		result = cursor.fetchall()

		#if an entry for that time of day already exists result will contain the entry id
		#if no entry exists result will contain []

		#if result is empty
		#there is no previous entry for this tod
		if not result:
			# symptom_entry_id = max id in table + 1
			query = "SELECT MAX(sym_entry_id) AS maximum from symptomEntry LIMIT 1;"
			cursor.execute(query)
			result = cursor.fetchall()

			if result[0][0] is None:
				new_sym_entry_id = 0
			else:
				new_sym_entry_id = result[0][0] + 1

			query = "INSERT INTO entries (user_id, entry_date, entry_tod, entry_emo_id, symptom_entry_id, notes) VALUES (%s, %s, %s, %s, %s, %s);"
			cursor.execute(query, (user_id, formatted_date, entry_tod, entry_emo_id, new_sym_entry_id, notes))
			db.commit()

			# symptoms contains a list of strings e.g. [ "acne 2", "insomnia 2" ]
			# this needs to be changed to the format: [['acne', 2], ['insomnia', 2]] i.e. a list of lists

			symList = []
			for symptom in symptoms:
				x = symptom.split()
				x[1] = int(x[1])
				symList.append(x)

			# symList now contains the format : [ [ "acne", 2 ], [ "insomnia,", 2 ] ]

			updatedlist = []

			for symptom in symList:
				sym_name = symptom[0]
				query = "SELECT sym_id FROM symptoms WHERE sym_name = '%s';"
				cursor.execute(query % sym_name)
				result = cursor.fetchone()
				updatedlist.append([result[0], symptom[1]])
			# at this point, updated list is a list of lists
			# with the format: [[symptom id, symptom severity],[symptom id, symptom severity], .....]

			for record in updatedlist:
				query = "INSERT INTO symptomEntry (sym_entry_id, symptom_entry_sev, sym_id) VALUES ( %s, %s, %s);"
				cursor.execute(query, (new_sym_entry_id, record[1], record[0]))
				db.commit()
			cursor.close()
			return "{'status': 'success'}"
		else:

			# update the emotion
			query = "UPDATE entries SET entry_emo_id = '%s' WHERE user_id = '%s' AND entry_date = '%s' AND entry_tod = '%s' "
			cursor.execute(query % (entry_emo_id,user_id, formatted_date, entry_tod))
			db.commit()

			#update the notes only if they have entered notes. This means that blank notes wont override the notes previously entered.
			if notes:
				# update the notes
				query = "UPDATE entries SET notes = '%s' WHERE user_id = '%s' AND entry_date = '%s' AND entry_tod = '%s' "
				cursor.execute(query % (notes, user_id, formatted_date, entry_tod))
				db.commit()

			query = "SELECT symptom_entry_id FROM entries WHERE user_id = '%s' AND entry_date = '%s' AND entry_tod = '%s';"
			cursor.execute(query % (user_id, formatted_date, entry_tod))
			result = cursor.fetchall()
			symptom_entry_id = result[0][0]

			query = "SELECT * FROM symptomEntry WHERE sym_entry_id = '%s';"
			cursor.execute(query % symptom_entry_id)
			result = cursor.fetchall()

			#result contains a list of the symptoms already logged for previous entry this tod
			# list is in format of [[symptom_entry_id, symptom_entry_sev,sym_id] , [....] ]

			#to get rid of the symptom entry id from the list
			existing_Symptoms = []
			for entry in result:
				existing_Symptoms.append([entry[2],entry[1]])

			symList = []
			for symptom in symptoms:
				x = symptom.split()
				x[1] = int(x[1])
				symList.append(x)

			# symList now contains the format : [ [ "acne", 2 ], [ "insomnia,", 2 ] ]

			newSymptoms = []

			for symptom in symList:
				sym_name = symptom[0]
				query = "SELECT sym_id FROM symptoms WHERE sym_name = '%s';"
				cursor.execute(query % sym_name)
				result = cursor.fetchone()
				newSymptoms.append([result[0], symptom[1]])

			#at this point:
			#existing_Symptoms contains a list in the format of symptom_id, symptom_severity that already EXISTS IN DB for this entry
			#newSymptoms contains the symptoms that were input by the user VIA UI not yet logged in the format of symptom_id, symptom_severity that already exists in db for this entry

			#to update any existing in the db and have newSymptoms left with only new ones to add to db

			i = []
			for new in newSymptoms:
				s_name = new[0]
				s_sev = new[1]

				for existing in existing_Symptoms:
					if existing[0] == s_name:
						i.append(new)
						query = "UPDATE symptomEntry SET symptom_entry_sev = '%s' WHERE sym_entry_id = '%s' AND sym_id = '%s';"
						cursor.execute(query % (s_sev, symptom_entry_id, s_name))
						db.commit()
			for entry in i:
				newSymptoms.remove(entry)

			#newSymptos now contains the entries that are new (didn't need to be updated)
			for entry in newSymptoms:
				query = "INSERT INTO symptomEntry (sym_entry_id, symptom_entry_sev, sym_id) VALUES ( %s, %s, %s);"
				cursor.execute(query, (symptom_entry_id, entry[1], entry[0]))
				db.commit()

		cursor.close()
		return "{'status': 'success'}"

	except Exception as e:
		error = "{'error': " + str(e) + "}"
	return error

#returning info from a particular day
@app.route('/history/getdayinfo/<user_id>/<target_date>/', methods = ['GET'])
@cross_origin()
def getdayinfo(user_id, target_date):
	try:
		result_dict = {}
		cursor = db.cursor()
		query = "SELECT symptom_entry_id FROM entries WHERE user_id = '%s' AND entry_date = '%s' AND entry_tod = '%s';"
		notesquery = "SELECT notes FROM entries WHERE user_id = '%s' AND entry_date = '%s' AND entry_tod = '%s';"
		emoquery = "SELECT entry_emo_id FROM entries WHERE user_id = '%s' AND entry_date = '%s' AND entry_tod = '%s';"

		#morning
		cursor.execute(query % (user_id, target_date, 'morning'))
		morning = cursor.fetchall()

		#afternoon
		cursor.execute(query % (user_id, target_date, 'afternoon'))
		afternoon = cursor.fetchall()

		#evening
		cursor.execute(query % (user_id, target_date, 'evening'))
		evening = cursor.fetchall()

		#night
		cursor.execute(query % (user_id, target_date, 'night'))
		night = cursor.fetchall()


		if morning:
			morning_symptom_entry_id = morning[0][0]
			query = "SELECT symptom_entry_sev, sym_id FROM symptomEntry WHERE sym_entry_id = '%s';"
			cursor.execute(query % morning_symptom_entry_id)
			result = cursor.fetchall()
			#[[symptom severity, symptom id]]
			#swap symptom id for the symptom name
			x = []
			for entry in result:
				id = entry[1]
				severity = entry[0]
				query = "SELECT sym_name FROM symptoms WHERE sym_id = '%s';"
				cursor.execute(query % id)
				result = cursor.fetchall()
				name = result[0][0]
				if severity == 1:
					new_sev = "(low) "
				elif severity == 2:
					new_sev = "(moderate) "
				elif severity == 3:
					new_sev = "(severe) "
				x.append([name+ " " + new_sev])
			result_dict['morning'] = x
			cursor.execute(notesquery % (user_id, target_date, 'morning'))
			notes = cursor.fetchall()
			if notes:
				result_dict['morning_note'] = notes
			cursor.execute(emoquery % (user_id, target_date, 'morning'))
			emo_id = cursor.fetchall()
			if emo_id:
				result_dict['morning_emo'] = emo_id




		if afternoon:
			afternoon_symptom_entry_id = afternoon[0][0]
			query = "SELECT symptom_entry_sev, sym_id FROM symptomEntry WHERE sym_entry_id = '%s';"
			cursor.execute(query % afternoon_symptom_entry_id)
			result = cursor.fetchall()
			# [[symptom severity, symptom id]]
			# swap symptom id for the symptom name
			x = []
			for entry in result:
				id = entry[1]
				severity = entry[0]
				query = "SELECT sym_name FROM symptoms WHERE sym_id = '%s';"
				cursor.execute(query % id)
				result = cursor.fetchall()
				name = result[0][0]
				if severity == 1:
					new_sev = "(low) "
				elif severity == 2:
					new_sev = "(moderate) "
				elif severity == 3:
					new_sev = "(severe) "
				x.append([name+ " " + new_sev])
			result_dict['afternoon'] = x
			cursor.execute(notesquery % (user_id, target_date, 'afternoon'))
			notes = cursor.fetchall()
			if notes:
				result_dict['afternoon_note'] = notes
			cursor.execute(emoquery % (user_id, target_date, 'afternoon'))
			emo_id = cursor.fetchall()
			if emo_id:
				result_dict['afternoon_emo'] = emo_id

		if evening:
			evening_symptom_entry_id = evening[0][0]
			query = "SELECT symptom_entry_sev, sym_id FROM symptomEntry WHERE sym_entry_id = '%s';"
			cursor.execute(query % (evening_symptom_entry_id))
			result = cursor.fetchall()
			# [[symptom severity, symptom id]]
			# swap symptom id for the symptom name
			x = []
			for entry in result:
				id = entry[1]
				severity = entry[0]
				query = "SELECT sym_name FROM symptoms WHERE sym_id = '%s';"
				cursor.execute(query % id)
				result = cursor.fetchall()
				name = result[0][0]
				if severity == 1:
					new_sev = "(low) "
				elif severity == 2:
					new_sev = "(moderate) "
				elif severity == 3:
					new_sev = "(severe) "
				x.append([name+ " " + new_sev])
			result_dict['evening'] = x
			cursor.execute(notesquery % (user_id, target_date, 'evening'))
			notes = cursor.fetchall()
			if notes:
				result_dict['evening_note'] = notes
			cursor.execute(emoquery % (user_id, target_date, 'evening'))
			emo_id = cursor.fetchall()
			if emo_id:
				result_dict['evening_emo'] = emo_id


		if night:
			night_symptom_entry_id = night[0][0]
			query = "SELECT symptom_entry_sev, sym_id FROM symptomEntry WHERE sym_entry_id = '%s';"
			cursor.execute(query % (night_symptom_entry_id))
			result = cursor.fetchall()
			# [[symptom severity, symptom id]]
			# swap symptom id for the symptom name
			x = []
			for entry in result:
				id = entry[1]
				severity = entry[0]
				query = "SELECT sym_name FROM symptoms WHERE sym_id = '%s';"
				cursor.execute(query % id)
				result = cursor.fetchall()
				name = result[0][0]
				if severity == 1:
					new_sev = "(low) "
				elif severity == 2:
					new_sev = "(moderate) "
				elif severity == 3:
					new_sev = "(severe) "
				x.append([name+ " " + new_sev])
			result_dict['night'] = x
			cursor.execute(notesquery % (user_id, target_date, 'night'))
			notes = cursor.fetchall()
			if notes:
				result_dict['night_note'] = notes
			cursor.execute(emoquery % (user_id, target_date, 'night'))
			emo_id = cursor.fetchall()
			if emo_id:
				result_dict['night_emo'] = emo_id

		#result_dict consists of a dict with format: { "evening": [ [ 2, "acne" ], [ 2, "insomnia" ] ], "morning": [ [ 2, "acne" ] ], "night": [ [ 2, "acne" ], [ 2, "insomnia" ] ] }



		cursor.close()
		return jsonify(result_dict)



	except Exception as e:
		error = "{'error': " + str(e) + "}"
		return error
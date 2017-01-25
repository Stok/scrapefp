#! /usr/bin/python3
#

import cgi, cgitb
import requests, operator, functools
from datetime import datetime as dt
from datetime import timedelta
from bs4 import BeautifulSoup
	
cgitb.enable()
form = cgi.FieldStorage()

def getCountryCodes(url):
        #This part gets the list of country codes
        r = requests.get(url)
        print(r.status_code, r.reason)
        content = r.text.encode('ascii', 'ignore')

        soup = BeautifulSoup(content, 'html.parser')
        countriesRaw = soup.find_all('option')

        return [(c.getText(), c.get('value')) for c in allCountries]

def getChangeDates(url, countryCode) :
        #This part gets the dates that the rate got changed
        r = requests.get(url + countryCode)
        print(r.status_code, r.reason)
        content = r.text.encode('ascii', 'ignore')

        soup = BeautifulSoup(content, 'html.parser')

        changeDatesRaw = soup.find(id='edit-date').find_all('option')
        return [date.get('value') for date in changeDatesRaw]


def getValueAtDate(url, countryCode, date, valueID):
        #This part gets the value for a particular date
        payload = {
                'date' : date.strftime("%Y-%m-%d %H:%M:%S")
        }
        r = requests.post(url + countryCode, payload)
        print(r.status_code, r.reason)
        content = r.text.encode('ascii', 'ignore')

        soup = BeautifulSoup(content, 'html.parser')
        return float(soup.find(id=valueID).get('value').replace(",", "."))

def makeDateTable(departureDate, returnDate):
        interval = (returnDate.replace(hour = 0) - departureDate.replace(hour = 0)).days
        relevantDates = [(departureDate.replace(hour = 0) + timedelta(days=x)) for x in range(0, interval + 1)] 
        return relevantDates

def getRefDate(refDates, travelDate):
        return [dt.strptime(rd, "%Y-%m-%d %H:%M:%S") for rd in redDates if travelDate >= dt.strptime(rd, "%Y-%m-%d %H:%M:%S")]

def getValueTable(dateTable, url, valueID, countryCode):
        refDates = getChangeDates(url, countryCode)
        refDateTable = [refDateTable.append(getRefDate(refDates, d)) for d in dateTable]
        valueTable = []
        tempDict = dict()
        for rd in refDateTable:
                try:
                        valueTable.append(tempDict[rd])
                except KeyError:
                        tempDict[rd] = getValueAtDate(url, countryCode, rd, valueID)
                        valueTable.append(tempDict[rd])
        return valueTable

def getWeights(dateTable, departureDate, returnDate, mealNumberCap):
        mealNumber = 0
        weights = []
        for d in dateTable:
                if d.date() == departureDate.date() :
                        if departureDate.hour < 13:
                                mc = mealcoeff(0, mealNumber, 2, mealNumberCap)
                                mealNumber = mealNumber + mc
                                weights.append(0.65 + 0.175 * mc)
                        elif 13 <= departureDate.hour < 21:
                                mc = mealcoeff(0, mealNumber, 1, mealNumberCap)
                                mealNumber = mealNumber + mc
                                weights.append(0.65 + 0.175 * mc)
                        else:
                                weights.append(0.65)
                elif d.date() == returnDate.date():
                        if returnDate.hour < 13:
                                weights.append(0)
                        elif 13 <= returnDate.hour < 21:
                                mc = mealcoeff(0, mealNumber, 1, mealNumberCap)
                                mealNumber = mealNumber + mc
                                weights.append(0.175 * mc)
                        else:
                                mc = mealcoeff(0, mealNumber, 2, mealNumberCap)
                                mealNumber = mealNumber + mc
                                weights.append(0.175 * mc)
                else:
                        mc = mealcoeff(0, mealNumber, 2, mealNumberCap)
                        mealNumber = mealNumber + mc
                        weights.append(0.65 + 0.175 * mc)
        return weights

def mealcoeff(result, mn, maxN, mCap):
        if result < maxN and mn < mCap :
                result = mealcoeff(result + 1, mn + 1, maxN, mCap)
                return result
        else :
                return result


def CalculateAmountDue(departureDate, returnDate, countryCode, mealNumberCap):

        dateTable = makeDateTable(departureDate, returnDate)
        d = (x.date() for x in dateTable)
        
        baremeTable = getValueTable(dateTable, 'http://www.economie.gouv.fr/dgfip/mission_taux_chancellerie/frais_resultat/', 'edit-bareme1', countryCode)

        tauxTable = getValueTable(dateTable, 'http://www.economie.gouv.fr/dgfip/taux_chancellerie_change_resultat/pays/', 'edit-taux', countryCode)
        
        weights = getWeights(dateTable, departureDate, returnDate, 10000)
        
        table = zip(baremeTable, tauxTable, weights)
        
        amountDue = sum(functools.reduce(mul, t) for t in table)
        
        newWeights = getWeights(dateTable, departureDate, returnDate, mealNumberCap)
        
        table2 = zip(baremeTable, tauxTable, newWeights)
        amountDue2 = sum(functools.reduce(mul, t) for t in table2)
        
        return [dateTable, baremeTable, tauxTable, weights, amountDue, mealNumberCap, newWeights, amountDue2]


print("Content-type:text/html\n\n")
print("")

departure_date = form.getvalue('departure_date')
return_date  = form.getvalue('return_date')
country_code = form.getvalue('country_code')
meal_cap = form.getvalue('meal_cap')

#For testing
#departure_date = "01/04/16_10:00"
#return_date  = "04/04/16_20:00"
#country_code = "GB"
#meal_cap = "5"

departureDate = dt.strptime(departure_date, "%d/%m/%y_%H:%M")
returnDate = dt.strptime(return_date, "%d/%m/%y_%H:%M")
mealNumberCap = int(meal_cap)

result = CalculateAmountDue(departureDate, returnDate, country_code, mealNumberCap)


print("<html><head><meta content='text/html; charset=UTF-8' />")
print("<title>Calculatrice Missions</title>")
print("</head>")
print("<body>")
print("<div>Vous avez indique que la mission a  " + country_code + "  se deroulera durant les dates suivants : %s </div> " % list(map(lambda x : x.strftime('%d/%m/%Y'), result[0])))
print("<div>Voici le bareme pour chacun des jours: %s</div>" % result[1])
print("<div>Les taux de change pour chacun des jours: %s</div>" % result[2])
print("<div>Le pourcentage du bareme que lagent peut recevoir, par jour: %s</div>" % list(map(lambda x : 100 * x, result[3])))
print("<div>Le montant total selon le forfait est donc de : %s</div>" % result[4])
print("<div>lagent a demande a etre rembourse pour %s repas.</div>" % result[5])
print("<div>Les pourcentages sont donc reajustes : %s</div>" % list(map(lambda x : 100 * x, result[6])))
print("<div>Le montant plafonne est : %s</div>" % result[7])
print("<div>Calcul termine. Bonne journee!</div>")
print("</body>")
print("</html>")

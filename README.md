ISO 20022 Screening Engine

The code screens ISO 20022 messages against OFAC, UN, EU, UK, SECO, AU, and CA sanctions lists to detect prohibited parties.
The engine receives an ISO 20022 XML file via API, it parses it to extract the structured data, it runs the data against the sanctions list database, it matches name/address/other identifying information and returns a response with a risk score, a response code, the top matches.



API.py
Has /health and /ready checks, and /screen endpoint accepts ISO 20022 XML. /refresh-lists will build the sanctions database.

Engine.py
Calls everything.

Isoparser.py
Takes in raw XML and breaks it down to take in information for all parties in ISO 20022 XML that can be screened.

Xload.py (SECOload.py, OFACload.py, etc.)
Downloads a sanctions list from a source and breaks it down to put it into the database.

Database.py
Used to create the initial sanctions database and retrieves needed information.

Matcher.py
Compares ISO parties against sanctions list.

Screening.py
Returns the response message for the screening.
Example:





Pythonrun.py
Offline testing tool I used to fine-tune matching.



Default Response Codes / Risk Levels (change on rules.py):


RISKLEVEL\_DEFAULT = { #Change Risk Levels

&nbsp;   "veryHighFrom": 0.90,

&nbsp;   "highFrom": 0.70,

&nbsp;   "moderateFrom": 0.25,

&nbsp;   "slightAbove": 0.10,

}



RESPONSECODE\_RULES\_PATH = Path(os.getenv("AML\_RESPONSECODE\_RULES\_PATH", Path(\_\_file\_\_).parent / "responsecode\_rules.json"))

RESPONSECODE\_DEFAULT = { #Change Response Codes

&nbsp;   "very high risk": "VERY\_HIGH\_RISK",

&nbsp;   "high risk": "HIGH\_RISK",

&nbsp;   "moderate risk": "MODERATE\_RISK",

&nbsp;   "slight risk": "SLIGHT\_RISK",

&nbsp;   "no risk": "NONE",

}







Example ISO20022 files in data\\iso


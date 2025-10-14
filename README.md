ISO 20022 Screening Engine

The code screens ISO 20022 messages against OFAC, UN, EU, UK, SECO, AU, and CA sanctions lists to detect prohibited parties.
The engine receives an ISO 20022 XML file via API, it parses it to extract the structured data, it runs the data against the sanctions list database, it matches name/address/other identifying information and returns a response with a risk score, a response code, the top matches. 


API.py
Has /health and /ready checks, and /screen endpoint accepts ISO 20022 XML.

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



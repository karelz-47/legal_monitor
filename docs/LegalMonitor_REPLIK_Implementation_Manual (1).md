# LegalMonitor — REPLIK API Implementation Manual

**Purpose:** developer blueprint for replacing / supplementing Slovensko.Digital OV sync-only calls with direct searchable REPLIK API calls.

**Target app:** LegalMonitor  
**Primary source:** IS REPLIK — Register predinsolvenčných, likvidačných a insolvenčných konaní  
**API style:** SOAP/XML via WSDL, not REST/JSON  
**Recommended integration pattern:** API connector + normalized JSON + 24h query cache + raw XML audit section

---

## 1. Executive implementation decision

LegalMonitor should use REPLIK as a **live search connector** for current and future insolvency / restructuring / liquidation records.

The app should expose three UI search regimes:

1. **Search by IČO** — default for company screening.
2. **Full-text search** — fallback when the user has only name, partial name, surname, or court file reference.
3. **Search by date period** — monitoring/admin/search-period mode.

The connector should call REPLIK, parse XML to normalized JSON, display user-friendly cards/timelines, and retain raw XML/parsed raw object in a collapsible “Source data” section for completeness review.

---

## 2. Official endpoints

### 2.1 Production WSDLs

```text
Konania / proceedings:
https://replik-ws.justice.sk/ru-verejnost-ws/konanieService.wsdl

Verejné oznamy / public notices:
https://replik-ws.justice.sk/ru-verejnost-ws/oznamService.wsdl
```

### 2.2 Test WSDLs

```text
Konania / proceedings:
https://replik-wst.justice.sk/ru-verejnost-ws/konanieService.wsdl

Verejné oznamy / public notices:
https://replik-wst.justice.sk/ru-verejnost-ws/oznamService.wsdl
```

### 2.3 SOAP namespace hints

Use a WSDL-generated client where possible. If raw SOAP must be handcrafted, the public examples use these namespaces:

```xml
xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
xmlns:dat="datatypes.konanie.verejnost.ru.sk.hp.com"
xmlns:dat="datatypes.oznam.verejnost.ru.sk.hp.com"
```

Use the WSDL as the source of truth for binding, operation names and final request wrappers.

---

## 3. Access, registration, cost and rate limits

### 3.1 Production access

The public API manual states that the production service is available to the public **without registration**.

### 3.2 Test access

The test environment requires registration. The registration should include:

- company contact details,
- employee/contact person details,
- IP address or IP range from which the test API will be accessed.

### 3.3 Cost

The official public API manual does **not** state any fee. Treat production access as public/free unless the Ministry later publishes different conditions or contractual terms.

### 3.4 Rate limits

No explicit per-second, per-minute or per-day rate limit was found in the public manual.

The documented operational limit is:

```text
VysledkovNaStranku: maximum 100 results per page
Stranka: page number starts at 0
```

Recommended LegalMonitor throttling even without published rate limits:

```text
Default page size: 50 or 100
Maximum page size sent to API: 100
Maximum concurrent REPLIK calls per app instance: 1–2
HTTP/SOAP timeout: 20–30 seconds
Retries: max 2 retries for network/5xx faults
Backoff: exponential, e.g. 1s -> 3s
Cache: 24 hours by normalized query key
```

---

## 4. REPLIK operations inventory

## 4.1 Proceedings service — `konanieService`

| Operation | Purpose | Use in LegalMonitor |
|---|---|---|
| `getKonaniePodlaICO` | Returns proceedings where debtor IČO equals searched IČO | Main exact company screening |
| `vyhladajKonanie` | Full-text search across proceeding reference, debtor IČO, debtor name/business name, surname | Name-based search regime |
| `getKonaniePreObdobie` | Returns proceedings where proceeding start date falls within date interval | Period search regime |
| `getKonanieDetail` | Returns detailed proceeding data by `KonanieId` | Detail enrichment after list search |
| `getKonanieDetailPodlaZnackyASudu` | Returns detailed proceeding data by court file reference + court code | Optional fallback/enrichment |
| `getZoznamSudov` | Returns court code/name list | Cache court code mapping |
| `vyhladajPoslednuZmenuOd` | Returns proceedings changed since timestamp | Optional background sync/change monitoring |

## 4.2 Public notices service — `oznamService`

| Operation | Purpose | Use in LegalMonitor |
|---|---|---|
| `getVerejneOznamyPodlaICO` | Returns public notices where debtor IČO equals searched IČO | Main exact company screening |
| `getVerejneOznamyPreObdobie` | Returns notices where publication date falls within date interval | Period search regime |
| `getVerejnyOznamPodlaZnackyASudu` | Returns notices by court file reference + court code | Enrichment after full-text proceeding result |
| `getVerejnyOznamDetail` | Returns full public notice text/detail by `OznamId` | Detail enrichment for selected notices |

---

## 5. UI search regimes and backend call flows

## 5.1 Regime A — Search by IČO

### UI purpose

This should be the default mode for company screening. It gives the cleanest match because the API searches debtor IČO exactly.

### User input

```json
{
  "searchRegime": "ICO",
  "ico": "34140469",
  "includeDetails": true,
  "pageSize": 100
}
```

### Input validation

```text
1. Strip spaces and non-digit characters.
2. Preserve leading zeroes if present.
3. Accept only 8 digits for Slovak IČO in normal company search.
4. Reject empty / malformed value with user-facing validation message.
```

### API calls

1. `konanieService.getKonaniePodlaICO`
2. `oznamService.getVerejneOznamyPodlaICO`
3. Optional detail enrichment:
   - `getKonanieDetail` for each proceeding returned in list
   - `getVerejnyOznamDetail` for each notice displayed in detail/timeline view

### Request object — generated SOAP client

```ts
const request = {
  Ico: "34140469",
  Stranka: 0,
  VysledkovNaStranku: 100,
  TypTriedenia: "DatumPoslednejUdalosti"
};
```

### Raw SOAP envelope example — proceedings by IČO

```xml
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:dat="datatypes.konanie.verejnost.ru.sk.hp.com">
  <soapenv:Header/>
  <soapenv:Body>
    <dat:getKonaniePodlaICORequest>
      <dat:Ico>34140469</dat:Ico>
      <dat:Stranka>0</dat:Stranka>
      <dat:VysledkovNaStranku>100</dat:VysledkovNaStranku>
      <dat:TypTriedenia>DatumPoslednejUdalosti</dat:TypTriedenia>
    </dat:getKonaniePodlaICORequest>
  </soapenv:Body>
</soapenv:Envelope>
```

### Raw SOAP envelope example — notices by IČO

```xml
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:dat="datatypes.oznam.verejnost.ru.sk.hp.com">
  <soapenv:Header/>
  <soapenv:Body>
    <dat:getVerejneOznamyPodlaICORequest>
      <dat:Ico>34140469</dat:Ico>
      <dat:Stranka>0</dat:Stranka>
      <dat:VysledkovNaStranku>100</dat:VysledkovNaStranku>
    </dat:getVerejneOznamyPodlaICORequest>
  </soapenv:Body>
</soapenv:Envelope>
```

### Pagination logic

```text
Start with Stranka = 0.
Read VysledkovCelkom.
If returned items < VysledkovCelkom, increment Stranka and repeat.
Stop when collected items >= VysledkovCelkom or when page has no items.
Do not request VysledkovNaStranku > 100.
```

---

## 5.2 Regime B — Full-text search

### UI purpose

Use when the user enters a company name, person name, partial name, surname, IČO-like text, or court file reference but exact IČO is unavailable.

### User input

```json
{
  "searchRegime": "FULL_TEXT",
  "query": "NOVIS",
  "sort": "Relevancia",
  "includeDetails": true,
  "includeRelatedNotices": true,
  "pageSize": 100
}
```

### API calls

1. `konanieService.vyhladajKonanie`
2. Optional detail enrichment:
   - `getKonanieDetail(KonanieId)`
3. Optional related notices:
   - for each returned proceeding with `SpisovaZnackaSudu` and `Sud`, call `oznamService.getVerejnyOznamPodlaZnackyASudu`

### Request object — generated SOAP client

```ts
const request = {
  Query: "NOVIS",
  Stranka: 0,
  VysledkovNaStranku: 100,
  TypTriedenia: "Relevancia"
};
```

### Raw SOAP envelope example

```xml
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:dat="datatypes.konanie.verejnost.ru.sk.hp.com">
  <soapenv:Header/>
  <soapenv:Body>
    <dat:vyhladajKonanieRequest>
      <dat:Query>NOVIS</dat:Query>
      <dat:Stranka>0</dat:Stranka>
      <dat:VysledkovNaStranku>100</dat:VysledkovNaStranku>
      <dat:TypTriedenia>Relevancia</dat:TypTriedenia>
    </dat:vyhladajKonanieRequest>
  </soapenv:Body>
</soapenv:Envelope>
```

### Sorting values

```text
DatumPoslednejUdalosti
DatumZacatiaKonania
Relevancia
```

### Important UI warning

Full-text search can return false positives. UI should label the mode clearly:

```text
Search mode: Full-text match
Review the debtor name/IČO and court file reference before treating the result as a match.
```

---

## 5.3 Regime C — Search by date period

### UI purpose

Use for monitoring and period checks, for example “show all proceedings/notices published or started between dates”.

### User input

```json
{
  "searchRegime": "PERIOD",
  "dateFrom": "2026-05-01",
  "dateTo": "2026-05-28",
  "includeProceedings": true,
  "includeNotices": true,
  "pageSize": 100
}
```

### API calls

1. `konanieService.getKonaniePreObdobie`
2. `oznamService.getVerejneOznamyPreObdobie`
3. Optional detail enrichment:
   - `getKonanieDetail`
   - `getVerejnyOznamDetail`

### Request object — proceedings by period

```ts
const request = {
  DatumOd: "2026-05-01",
  DatumDo: "2026-05-28",
  Stranka: 0,
  VysledkovNaStranku: 100
};
```

### Raw SOAP envelope — proceedings by period

```xml
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:dat="datatypes.konanie.verejnost.ru.sk.hp.com">
  <soapenv:Header/>
  <soapenv:Body>
    <dat:getKonaniePreObdobieRequest>
      <dat:DatumOd>2026-05-01</dat:DatumOd>
      <dat:DatumDo>2026-05-28</dat:DatumDo>
      <dat:Stranka>0</dat:Stranka>
      <dat:VysledkovNaStranku>100</dat:VysledkovNaStranku>
    </dat:getKonaniePreObdobieRequest>
  </soapenv:Body>
</soapenv:Envelope>
```

### Raw SOAP envelope — notices by period

```xml
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:dat="datatypes.oznam.verejnost.ru.sk.hp.com">
  <soapenv:Header/>
  <soapenv:Body>
    <dat:getVerejneOznamyPreObdobieRequest>
      <dat:DatumOd>2026-05-01</dat:DatumOd>
      <dat:DatumDo>2026-05-28</dat:DatumDo>
      <dat:Stranka>0</dat:Stranka>
      <dat:VysledkovNaStranku>100</dat:VysledkovNaStranku>
    </dat:getVerejneOznamyPreObdobieRequest>
  </soapenv:Body>
</soapenv:Envelope>
```

### Recommended app guardrail

For public UI, limit date ranges to avoid heavy calls:

```text
Default maximum date range: 31 days
Admin maximum date range: 365 days, with explicit confirmation
Always paginate
Do not auto-enrich detail for thousands of rows
```

---

## 6. Detail calls

## 6.1 Proceeding detail by ID

### Request object

```ts
const request = {
  KonanieId: 9770
};
```

### SOAP envelope

```xml
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:dat="datatypes.konanie.verejnost.ru.sk.hp.com">
  <soapenv:Header/>
  <soapenv:Body>
    <dat:getKonanieDetailRequest>
      <dat:KonanieId>9770</dat:KonanieId>
    </dat:getKonanieDetailRequest>
  </soapenv:Body>
</soapenv:Envelope>
```

## 6.2 Proceeding detail by court file reference and court

### Request object

```ts
const request = {
  KonanieZnacka: "2K/98/2016",
  KonanieSud: "139"
};
```

### SOAP envelope

```xml
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:dat="datatypes.konanie.verejnost.ru.sk.hp.com">
  <soapenv:Header/>
  <soapenv:Body>
    <dat:getKonanieDetailPodlaZnackyASuduRequest>
      <dat:KonanieZnacka>2K/98/2016</dat:KonanieZnacka>
      <dat:KonanieSud>139</dat:KonanieSud>
    </dat:getKonanieDetailPodlaZnackyASuduRequest>
  </soapenv:Body>
</soapenv:Envelope>
```

## 6.3 Public notice detail by ID

### Request object

```ts
const request = {
  OznamId: 244822
};
```

### SOAP envelope

```xml
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:dat="datatypes.oznam.verejnost.ru.sk.hp.com">
  <soapenv:Header/>
  <soapenv:Body>
    <dat:getVerejnyOznamDetailRequest>
      <dat:OznamId>244822</dat:OznamId>
    </dat:getVerejnyOznamDetailRequest>
  </soapenv:Body>
</soapenv:Envelope>
```

## 6.4 Public notices by court file reference and court

### Request object

```ts
const request = {
  SpisovaZnackaSudnehoSpisu: "60OdK/4/2018",
  SudKod: "102",
  Stranka: 0,
  VysledkovNaStranku: 100
};
```

### SOAP envelope

```xml
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:dat="datatypes.oznam.verejnost.ru.sk.hp.com">
  <soapenv:Header/>
  <soapenv:Body>
    <dat:getVerejnyOznamPodlaZnackyASuduRequest>
      <dat:SpisovaZnackaSudnehoSpisu>60OdK/4/2018</dat:SpisovaZnackaSudnehoSpisu>
      <dat:SudKod>102</dat:SudKod>
      <dat:Stranka>0</dat:Stranka>
      <dat:VysledkovNaStranku>100</dat:VysledkovNaStranku>
    </dat:getVerejnyOznamPodlaZnackyASuduRequest>
  </soapenv:Body>
</soapenv:Envelope>
```

---

## 7. Raw response structures and normalized JSON

## 7.1 `KonanieInfo` — proceeding list item

### Relevant raw fields

```text
Id
SpisovaZnackaSudu
Typ
DatumZacatiaKonania / DatumZacatiaKonanie
DatumZacatiaProcesu
DatumPodania
Dlznik
DlznikIco
DatumPoslednejUdalosti
Sud
SudNazov
Spravca
StavKonania
```

### Normalized model

```json
{
  "id": "9770",
  "sourceType": "proceeding",
  "caseReference": "CbR1/1/2025",
  "proceedingType": "LIKVIDACIA",
  "proceedingTypeLabel": {
    "sk": "Likvidácia",
    "en": "Liquidation"
  },
  "startDate": "2025-07-03",
  "processStartDate": "2025-07-03",
  "filingDate": "2025-07-01",
  "debtor": {
    "displayName": "Testlikvidacia",
    "ico": "34140469"
  },
  "lastEventDate": "2025-07-03",
  "court": {
    "code": "104",
    "name": "Mestský súd Bratislava III"
  },
  "administrator": {
    "displayName": "Semko Jozef, Ing."
  },
  "status": "ZASTAVENE_KONANIE",
  "uiSeverity": "warning"
}
```

## 7.2 `Konanie` — proceeding detail

### Relevant raw fields

```text
Id
SpisovaZnackaSudu
Typ
Navrhovatel
Dlznik
Sud
Sudca
Spravca
DatumZacatiaKonania
DatumZacatiaProcesu
TypSpravcu
```

### Normalized model

```json
{
  "id": "8647",
  "sourceType": "proceedingDetail",
  "caseReference": "2K/98/2016",
  "proceedingType": "KONKURZ",
  "debtors": [
    {
      "type": "corporate_or_person",
      "displayName": "eMTrade a.s.",
      "ico": "36628760",
      "address": {
        "street": null,
        "municipality": "Ladomerská Vieska",
        "postalCode": "96501",
        "country": "SVK"
      }
    }
  ],
  "petitioners": [],
  "court": {
    "code": "139",
    "name": "Okresný súd Banská Bystrica"
  },
  "judge": "Mgr. Zuzana Antalová",
  "administrator": {
    "displayName": "Insolvency Management Group k.s.",
    "ico": "51067820",
    "mark": "S1862"
  },
  "startDate": "2017-01-20",
  "processStartDate": "2017-03-09",
  "administratorType": "RIADNY"
}
```

Important parser note: Some XML-to-JS clients return `Konanie` as an object; newer manual versions state it can be an array where more than one occurrence exists for the same court reference + court. Always normalize to array.

```ts
function toArray<T>(value: T | T[] | null | undefined): T[] {
  if (value == null) return [];
  return Array.isArray(value) ? value : [value];
}
```

## 7.3 `VerejnyOznamInfo` — public notice list item

### Relevant raw fields

```text
OznamId
OznamTyp
SudKod
SudNazov
SpisovaZnackaSudnehoSpisu
KonanieId
KonanieTyp
DatumVydania
```

### Normalized model

```json
{
  "id": "244822",
  "sourceType": "publicNotice",
  "noticeType": "OZNAM_SUD",
  "noticeTypeLabel": {
    "sk": "Oznam súdu",
    "en": "Court notice"
  },
  "court": {
    "code": "102",
    "name": "Mestský súd Bratislava I"
  },
  "caseReference": "9OdK/4/2018",
  "proceedingId": "9518",
  "proceedingType": "ODDLZENIE-KONKURZ",
  "publishedDate": "2025-08-04",
  "uiSeverity": "info"
}
```

## 7.4 `VerejnyOznam` — public notice detail

### Relevant raw fields

```text
OznamId
OznamTyp
SudKod
SudNazov
SpisovaZnackaSudnehoSpisu
KonanieId
KonanieTyp
DatumVydania
ObsahujePrilohy
TextDruh
TextPoucenie
TextHlavicka
TextOdovodnenie
TextOznam
TextRozhodnutie
DruhPodania
Text
SpisovaZnackaSpravcovskehoSpisu
```

### Normalized model

```json
{
  "id": "244822",
  "sourceType": "publicNoticeDetail",
  "noticeType": "OZNAM_SUD",
  "court": {
    "code": "102",
    "name": "Mestský súd Bratislava I"
  },
  "caseReference": "9OdK/4/2018",
  "administratorCaseReference": null,
  "proceedingId": "9518",
  "proceedingType": "ODDLZENIE-KONKURZ",
  "publishedDate": "2025-08-04",
  "hasAttachments": false,
  "documentKind": "UZNESENIE",
  "filingKind": "INE_ZVEREJNENIE",
  "text": {
    "header": "...",
    "decision": "...",
    "reasoning": "...",
    "instruction": "...",
    "notice": "...",
    "administratorText": "..."
  }
}
```

---

## 8. Final LegalMonitor connector response envelope

Every REPLIK call should be transformed into a stable envelope similar to the existing LegalMonitor connector style.

```json
{
  "capturedAt": "2026-05-28T10:00:00.000Z",
  "connector": "replik",
  "status": "queried",
  "rows": 3,
  "error": null,
  "errorResponse": null,
  "searchRegime": "ICO",
  "query": {
    "ico": "34140469",
    "query": null,
    "dateFrom": null,
    "dateTo": null
  },
  "summary": {
    "hasProceedings": true,
    "proceedingsCount": 1,
    "publicNoticesCount": 2,
    "highestSeverity": "warning",
    "primaryFinding": "REPLIK records found for searched IČO."
  },
  "proceedings": [],
  "publicNotices": [],
  "requests": [
    {
      "service": "konanieService",
      "operation": "getKonaniePodlaICO",
      "params": {
        "Ico": "34140469",
        "Stranka": 0,
        "VysledkovNaStranku": 100,
        "TypTriedenia": "DatumPoslednejUdalosti"
      },
      "rows": 1,
      "rawResponse": {}
    }
  ],
  "raw": {
    "soapXml": {
      "konania": "...",
      "oznamy": "..."
    },
    "parsed": {
      "konania": {},
      "oznamy": {}
    }
  }
}
```

---

## 9. UI parsing and output design

## 9.1 Summary card

Render a high-level result first.

### No records

```text
No REPLIK records found for the searched IČO / query / period.
```

### Records found

```text
REPLIK records found
Proceedings: 1
Public notices: 2
Most recent event/publication: 2025-08-04
```

### Legal wording caution

Do not automatically write “company is bankrupt” solely because a record exists. Use neutral labels:

```text
Proceeding record found
Public notice found
Liquidation-related record found
Insolvency-related public notice found
```

## 9.2 Proceeding card fields

Show:

```text
Proceeding type
Case reference
Debtor name + IČO
Court
Status
Start date
Process start date
Last event date
Administrator / liquidator / trustee
```

## 9.3 Public notice timeline fields

Show:

```text
Publication date
Notice type
Document kind
Court
Case reference
Short text preview
Button: Show full notice
```

## 9.4 Raw source data section

Add a collapsible section:

```text
Source data / Technical details
- API service
- operation
- request parameters
- raw XML response
- normalized JSON
```

This is important for completeness checking and auditability.

---

## 10. i18n keys for UI

## 10.1 English

```json
{
  "replik.title": "REPLIK records",
  "replik.searchMode.ico": "Search by IČO",
  "replik.searchMode.fullText": "Full-text search",
  "replik.searchMode.period": "Search by date period",
  "replik.noRecords": "No REPLIK records found.",
  "replik.recordsFound": "REPLIK records found",
  "replik.proceedings": "Proceedings",
  "replik.publicNotices": "Public notices",
  "replik.caseReference": "Case reference",
  "replik.debtor": "Debtor",
  "replik.ico": "IČO",
  "replik.court": "Court",
  "replik.status": "Status",
  "replik.proceedingType": "Proceeding type",
  "replik.startDate": "Start date",
  "replik.processStartDate": "Process start date",
  "replik.lastEventDate": "Last event date",
  "replik.publicationDate": "Publication date",
  "replik.noticeType": "Notice type",
  "replik.documentKind": "Document kind",
  "replik.administrator": "Administrator / liquidator",
  "replik.showRaw": "Show source data",
  "replik.fullTextWarning": "Full-text search can include false positives. Review debtor identity before treating the record as a match.",
  "replik.sourceDisclaimer": "Data is shown as returned by IS REPLIK. Legal interpretation should be confirmed from the source record."
}
```

## 10.2 Slovak

```json
{
  "replik.title": "Záznamy REPLIK",
  "replik.searchMode.ico": "Vyhľadanie podľa IČO",
  "replik.searchMode.fullText": "Fulltextové vyhľadanie",
  "replik.searchMode.period": "Vyhľadanie podľa obdobia",
  "replik.noRecords": "V REPLIK neboli nájdené žiadne záznamy.",
  "replik.recordsFound": "Boli nájdené záznamy REPLIK",
  "replik.proceedings": "Konania",
  "replik.publicNotices": "Verejné oznamy",
  "replik.caseReference": "Spisová značka",
  "replik.debtor": "Dlžník",
  "replik.ico": "IČO",
  "replik.court": "Súd",
  "replik.status": "Stav",
  "replik.proceedingType": "Typ konania",
  "replik.startDate": "Dátum začatia konania",
  "replik.processStartDate": "Dátum začatia procesu",
  "replik.lastEventDate": "Dátum poslednej udalosti",
  "replik.publicationDate": "Dátum zverejnenia",
  "replik.noticeType": "Typ oznamu",
  "replik.documentKind": "Druh dokumentu",
  "replik.administrator": "Správca / likvidátor",
  "replik.showRaw": "Zobraziť zdrojové dáta",
  "replik.fullTextWarning": "Fulltextové vyhľadanie môže obsahovať nepresné zhody. Pred vyhodnotením zhody skontrolujte identitu dlžníka.",
  "replik.sourceDisclaimer": "Dáta sú zobrazené tak, ako ich vrátil IS REPLIK. Právny výklad je potrebné overiť zo zdrojového záznamu."
}
```

---

## 11. TypeScript implementation

## 11.1 Install packages

```bash
npm install soap fast-xml-parser p-limit crypto-js
npm install --save-dev @types/node typescript
```

Alternative: use Node built-in `crypto` instead of `crypto-js`.

## 11.2 Suggested file structure

```text
server/
  lib/
    connectors/
      replik/
        config.ts
        client.ts
        search.ts
        normalizers.ts
        cache.ts
        types.ts
```

## 11.3 `config.ts`

```ts
export type ReplikEnvironment = "production" | "test";

export const REPLIK_WSDL = {
  production: {
    konanie: "https://replik-ws.justice.sk/ru-verejnost-ws/konanieService.wsdl",
    oznam: "https://replik-ws.justice.sk/ru-verejnost-ws/oznamService.wsdl"
  },
  test: {
    konanie: "https://replik-wst.justice.sk/ru-verejnost-ws/konanieService.wsdl",
    oznam: "https://replik-wst.justice.sk/ru-verejnost-ws/oznamService.wsdl"
  }
} as const;

export const REPLIK_DEFAULTS = {
  pageSize: 100,
  timeoutMs: 30_000,
  cacheTtlSeconds: 86_400,
  defaultSort: "DatumPoslednejUdalosti" as const,
  maxConcurrentCalls: 2
};

export const REPLIK_SORT_VALUES = [
  "DatumPoslednejUdalosti",
  "DatumZacatiaKonania",
  "Relevancia"
] as const;

export type ReplikSort = typeof REPLIK_SORT_VALUES[number];
```

## 11.4 `types.ts`

```ts
export type SearchRegime = "ICO" | "FULL_TEXT" | "PERIOD";
export type UiSeverity = "none" | "info" | "warning" | "critical";

export interface NormalizedCourt {
  code: string | null;
  name: string | null;
}

export interface NormalizedDebtor {
  displayName: string | null;
  ico: string | null;
  address?: Record<string, string | null>;
}

export interface NormalizedProceeding {
  id: string | null;
  sourceType: "proceeding" | "proceedingDetail";
  caseReference: string | null;
  proceedingType: string | null;
  startDate: string | null;
  processStartDate: string | null;
  filingDate?: string | null;
  debtor?: NormalizedDebtor;
  debtors?: NormalizedDebtor[];
  lastEventDate?: string | null;
  court: NormalizedCourt;
  judge?: string | null;
  administrator?: {
    displayName: string | null;
    ico?: string | null;
    mark?: string | null;
  };
  status?: string | null;
  administratorType?: string | null;
  uiSeverity: UiSeverity;
  raw?: unknown;
}

export interface NormalizedPublicNotice {
  id: string | null;
  sourceType: "publicNotice" | "publicNoticeDetail";
  noticeType: string | null;
  court: NormalizedCourt;
  caseReference: string | null;
  administratorCaseReference?: string | null;
  proceedingId?: string | null;
  proceedingType: string | null;
  publishedDate: string | null;
  hasAttachments?: boolean | null;
  documentKind?: string | null;
  filingKind?: string | null;
  text?: {
    header?: string | null;
    decision?: string | null;
    reasoning?: string | null;
    instruction?: string | null;
    notice?: string | null;
    administratorText?: string | null;
  };
  uiSeverity: UiSeverity;
  raw?: unknown;
}

export interface ReplikConnectorResponse {
  capturedAt: string;
  connector: "replik";
  status: "queried" | "empty" | "error";
  rows: number;
  error: string | null;
  errorResponse: unknown | null;
  searchRegime: SearchRegime;
  query: {
    ico?: string | null;
    query?: string | null;
    dateFrom?: string | null;
    dateTo?: string | null;
  };
  summary: {
    hasProceedings: boolean;
    proceedingsCount: number;
    publicNoticesCount: number;
    highestSeverity: UiSeverity;
    primaryFinding: string;
  };
  proceedings: NormalizedProceeding[];
  publicNotices: NormalizedPublicNotice[];
  requests: Array<{
    service: "konanieService" | "oznamService";
    operation: string;
    params: Record<string, unknown>;
    rows: number;
    rawResponse?: unknown;
  }>;
  raw?: {
    parsed?: Record<string, unknown>;
    soapXml?: Record<string, string>;
  };
}
```

## 11.5 `client.ts`

```ts
import soap from "soap";
import { REPLIK_DEFAULTS, REPLIK_WSDL, ReplikEnvironment } from "./config";

export interface ReplikClients {
  konanie: soap.Client;
  oznam: soap.Client;
}

let cachedClients: Partial<Record<ReplikEnvironment, Promise<ReplikClients>>> = {};

export async function getReplikClients(
  env: ReplikEnvironment = "production"
): Promise<ReplikClients> {
  if (!cachedClients[env]) {
    cachedClients[env] = createClients(env);
  }
  return cachedClients[env]!;
}

async function createClients(env: ReplikEnvironment): Promise<ReplikClients> {
  const options: soap.IOptions = {
    timeout: REPLIK_DEFAULTS.timeoutMs,
    wsdl_options: {
      timeout: REPLIK_DEFAULTS.timeoutMs
    }
  };

  const [konanie, oznam] = await Promise.all([
    soap.createClientAsync(REPLIK_WSDL[env].konanie, options),
    soap.createClientAsync(REPLIK_WSDL[env].oznam, options)
  ]);

  return { konanie, oznam };
}

export async function callSoapOperation<T = unknown>(
  client: soap.Client,
  operation: string,
  params: Record<string, unknown>
): Promise<{ result: T; rawResponse?: string; rawRequest?: string }> {
  const methodName = `${operation}Async`;

  if (typeof (client as any)[methodName] !== "function") {
    throw new Error(`REPLIK SOAP operation not available on client: ${operation}`);
  }

  const [result, rawResponse, _soapHeader, rawRequest] = await (client as any)[methodName](params);

  return {
    result: result as T,
    rawResponse,
    rawRequest
  };
}
```

## 11.6 `normalizers.ts`

```ts
import { NormalizedProceeding, NormalizedPublicNotice, UiSeverity } from "./types";

export function toArray<T>(value: T | T[] | null | undefined): T[] {
  if (value == null) return [];
  return Array.isArray(value) ? value : [value];
}

export function clean(value: unknown): string | null {
  if (value == null) return null;
  const s = String(value).replace(/\s+/g, " ").trim();
  return s.length ? s : null;
}

export function normalizeDate(value: unknown): string | null {
  const s = clean(value);
  if (!s) return null;
  // Handles YYYY-MM-DD, ISO date-time and Slovak API timezone variants.
  const match = s.match(/^\d{4}-\d{2}-\d{2}/);
  return match ? match[0] : s;
}

export function normalizeIco(value: unknown): string | null {
  const s = clean(value);
  if (!s) return null;
  const digits = s.replace(/\D/g, "");
  return digits || null;
}

export function normalizeProceedingType(value: unknown): string | null {
  const s = clean(value);
  if (!s) return null;
  // Manual uses hyphen variants; some examples use underscore variants.
  return s.replace(/_/g, "-");
}

export function severityForProceeding(type: string | null, status?: string | null): UiSeverity {
  const t = normalizeProceedingType(type);
  const st = clean(status)?.toUpperCase() ?? "";

  if (!t) return "info";

  const isClosed =
    st.includes("SKONC") ||
    st.includes("ZASTAV") ||
    st.includes("UKONC") ||
    st.includes("KONIEC");

  if (isClosed) return "warning";

  if (["KONKURZ", "MALYKONKURZ", "RESTRUKTURALIZACIA", "LIKVIDACIA", "VPR"].includes(t)) {
    return "critical";
  }

  return "warning";
}

export function normalizeKonanieInfo(raw: any): NormalizedProceeding {
  const proceedingType = normalizeProceedingType(raw?.Typ);
  const status = clean(raw?.StavKonania);

  return {
    id: clean(raw?.Id),
    sourceType: "proceeding",
    caseReference: clean(raw?.SpisovaZnackaSudu),
    proceedingType,
    startDate: normalizeDate(raw?.DatumZacatiaKonania ?? raw?.DatumZacatiaKonanie),
    processStartDate: normalizeDate(raw?.DatumZacatiaProcesu),
    filingDate: normalizeDate(raw?.DatumPodania),
    debtor: {
      displayName: clean(raw?.Dlznik),
      ico: normalizeIco(raw?.DlznikIco)
    },
    lastEventDate: normalizeDate(raw?.DatumPoslednejUdalosti),
    court: {
      code: clean(raw?.Sud),
      name: clean(raw?.SudNazov)
    },
    administrator: {
      displayName: clean(raw?.Spravca)
    },
    status,
    uiSeverity: severityForProceeding(proceedingType, status),
    raw
  };
}

export function normalizeVerejnyOznamInfo(raw: any): NormalizedPublicNotice {
  const proceedingType = normalizeProceedingType(raw?.KonanieTyp);

  return {
    id: clean(raw?.OznamId),
    sourceType: "publicNotice",
    noticeType: clean(raw?.OznamTyp),
    court: {
      code: clean(raw?.SudKod),
      name: clean(raw?.SudNazov)
    },
    caseReference: clean(raw?.SpisovaZnackaSudnehoSpisu),
    proceedingId: clean(raw?.KonanieId),
    proceedingType,
    publishedDate: normalizeDate(raw?.DatumVydania),
    uiSeverity: "info",
    raw
  };
}

export function normalizeVerejnyOznamDetail(raw: any): NormalizedPublicNotice {
  const proceedingType = normalizeProceedingType(raw?.KonanieTyp);

  return {
    id: clean(raw?.OznamId),
    sourceType: "publicNoticeDetail",
    noticeType: clean(raw?.OznamTyp),
    court: {
      code: clean(raw?.SudKod),
      name: clean(raw?.SudNazov)
    },
    caseReference: clean(raw?.SpisovaZnackaSudnehoSpisu),
    administratorCaseReference: clean(raw?.SpisovaZnackaSpravcovskehoSpisu),
    proceedingId: clean(raw?.KonanieId),
    proceedingType,
    publishedDate: normalizeDate(raw?.DatumVydania),
    hasAttachments: raw?.ObsahujePrilohy == null ? null : String(raw.ObsahujePrilohy).toLowerCase() === "true",
    documentKind: clean(raw?.TextDruh),
    filingKind: clean(raw?.DruhPodania),
    text: {
      header: clean(raw?.TextHlavicka),
      decision: clean(raw?.TextRozhodnutie),
      reasoning: clean(raw?.TextOdovodnenie),
      instruction: clean(raw?.TextPoucenie),
      notice: clean(raw?.TextOznam),
      administratorText: clean(raw?.Text)
    },
    uiSeverity: "info",
    raw
  };
}
```

## 11.7 `cache.ts`

Example assumes PostgreSQL. Adjust table/schema names to current LegalMonitor conventions.

```sql
CREATE TABLE IF NOT EXISTS legalmonitor_replik_cache (
  id BIGSERIAL PRIMARY KEY,
  query_hash TEXT NOT NULL UNIQUE,
  search_regime TEXT NOT NULL,
  query_json JSONB NOT NULL,
  response_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_legalmonitor_replik_cache_expires
  ON legalmonitor_replik_cache (expires_at);
```

```ts
import crypto from "node:crypto";

export function cacheKey(input: unknown): string {
  const normalized = JSON.stringify(input, Object.keys(input as any).sort());
  return crypto.createHash("sha256").update(normalized).digest("hex");
}

export async function getCachedReplikResult(db: any, key: string) {
  const row = await db.oneOrNone(
    `SELECT response_json
       FROM legalmonitor_replik_cache
      WHERE query_hash = $1
        AND expires_at > NOW()`,
    [key]
  );
  return row?.response_json ?? null;
}

export async function setCachedReplikResult(
  db: any,
  key: string,
  searchRegime: string,
  query: unknown,
  response: unknown,
  ttlSeconds = 86_400
) {
  await db.none(
    `INSERT INTO legalmonitor_replik_cache
       (query_hash, search_regime, query_json, response_json, expires_at)
     VALUES ($1, $2, $3::jsonb, $4::jsonb, NOW() + ($5 || ' seconds')::interval)
     ON CONFLICT (query_hash)
     DO UPDATE SET
       response_json = EXCLUDED.response_json,
       expires_at = EXCLUDED.expires_at,
       created_at = NOW()`,
    [key, searchRegime, JSON.stringify(query), JSON.stringify(response), ttlSeconds]
  );
}
```

Safer stable stringify:

```ts
export function stableStringify(value: any): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${stableStringify(value[k])}`).join(",")}}`;
}
```

## 11.8 `search.ts` — core connector flow

```ts
import pLimit from "p-limit";
import { getReplikClients, callSoapOperation } from "./client";
import { REPLIK_DEFAULTS, ReplikSort } from "./config";
import {
  normalizeKonanieInfo,
  normalizeVerejnyOznamInfo,
  normalizeVerejnyOznamDetail,
  toArray
} from "./normalizers";
import { ReplikConnectorResponse, NormalizedProceeding, NormalizedPublicNotice } from "./types";

function pickList<T>(result: any, listKey: string, itemKey?: string): T[] {
  const list = result?.[listKey];
  if (!list) return [];

  // Depending on SOAP parser, list can be:
  // 1) array of items directly,
  // 2) object containing repeated child item,
  // 3) one single object.
  if (Array.isArray(list)) return list as T[];
  if (itemKey && list[itemKey]) return toArray<T>(list[itemKey]);
  return toArray<T>(list as T);
}

function totalCount(result: any): number {
  const n = Number(result?.VysledkovCelkom ?? 0);
  return Number.isFinite(n) ? n : 0;
}

async function paginate<T>(
  callPage: (page: number) => Promise<{ result: any; rows: T[] }>,
  maxPages = 100
): Promise<{ rows: T[]; rawResults: any[] }> {
  const rows: T[] = [];
  const rawResults: any[] = [];

  for (let page = 0; page < maxPages; page++) {
    const { result, rows: pageRows } = await callPage(page);
    rawResults.push(result);
    rows.push(...pageRows);

    const total = totalCount(result);
    if (pageRows.length === 0) break;
    if (total > 0 && rows.length >= total) break;
    if (pageRows.length < REPLIK_DEFAULTS.pageSize) break;
  }

  return { rows, rawResults };
}

export async function searchReplikByIco(input: {
  ico: string;
  includeDetails?: boolean;
  pageSize?: number;
  sort?: ReplikSort;
}): Promise<ReplikConnectorResponse> {
  const capturedAt = new Date().toISOString();
  const { konanie, oznam } = await getReplikClients("production");
  const pageSize = Math.min(input.pageSize ?? REPLIK_DEFAULTS.pageSize, 100);
  const sort = input.sort ?? REPLIK_DEFAULTS.defaultSort;
  const requests: ReplikConnectorResponse["requests"] = [];

  const proceedingsPage = await paginate<any>(async (page) => {
    const params = { Ico: input.ico, Stranka: page, VysledkovNaStranku: pageSize, TypTriedenia: sort };
    const { result } = await callSoapOperation(konanie, "getKonaniePodlaICO", params);
    const items = pickList<any>(result, "KonanieInfoList", "KonanieInfo");
    requests.push({ service: "konanieService", operation: "getKonaniePodlaICO", params, rows: items.length, rawResponse: result });
    return { result, rows: items };
  });

  const noticesPage = await paginate<any>(async (page) => {
    const params = { Ico: input.ico, Stranka: page, VysledkovNaStranku: pageSize };
    const { result } = await callSoapOperation(oznam, "getVerejneOznamyPodlaICO", params);
    const items = pickList<any>(result, "VerejnyOznamInfoList", "VerejnyOznamInfo");
    requests.push({ service: "oznamService", operation: "getVerejneOznamyPodlaICO", params, rows: items.length, rawResponse: result });
    return { result, rows: items };
  });

  const proceedings = proceedingsPage.rows.map(normalizeKonanieInfo);
  const publicNotices = noticesPage.rows.map(normalizeVerejnyOznamInfo);

  return buildResponse({
    capturedAt,
    searchRegime: "ICO",
    query: { ico: input.ico },
    proceedings,
    publicNotices,
    requests,
    raw: {
      parsed: {
        proceedingPages: proceedingsPage.rawResults,
        noticePages: noticesPage.rawResults
      }
    }
  });
}

export async function searchReplikFullText(input: {
  query: string;
  includeDetails?: boolean;
  includeRelatedNotices?: boolean;
  pageSize?: number;
  sort?: ReplikSort;
}): Promise<ReplikConnectorResponse> {
  const capturedAt = new Date().toISOString();
  const { konanie, oznam } = await getReplikClients("production");
  const pageSize = Math.min(input.pageSize ?? REPLIK_DEFAULTS.pageSize, 100);
  const sort = input.sort ?? "Relevancia";
  const requests: ReplikConnectorResponse["requests"] = [];

  const proceedingsPage = await paginate<any>(async (page) => {
    const params = { Query: input.query, Stranka: page, VysledkovNaStranku: pageSize, TypTriedenia: sort };
    const { result } = await callSoapOperation(konanie, "vyhladajKonanie", params);
    const items = pickList<any>(result, "KonanieInfoList", "KonanieInfo");
    requests.push({ service: "konanieService", operation: "vyhladajKonanie", params, rows: items.length, rawResponse: result });
    return { result, rows: items };
  });

  const proceedings = proceedingsPage.rows.map(normalizeKonanieInfo);
  let publicNotices: NormalizedPublicNotice[] = [];

  if (input.includeRelatedNotices) {
    const limit = pLimit(REPLIK_DEFAULTS.maxConcurrentCalls);
    const noticeBatches = await Promise.all(
      proceedings
        .filter(p => p.caseReference && p.court.code)
        .map(p => limit(async () => {
          const params = {
            SpisovaZnackaSudnehoSpisu: p.caseReference!,
            SudKod: p.court.code!,
            Stranka: 0,
            VysledkovNaStranku: pageSize
          };
          const { result } = await callSoapOperation(oznam, "getVerejnyOznamPodlaZnackyASudu", params);
          const items = pickList<any>(result, "VerejnyOznamInfoList", "VerejnyOznamInfo");
          requests.push({ service: "oznamService", operation: "getVerejnyOznamPodlaZnackyASudu", params, rows: items.length, rawResponse: result });
          return items.map(normalizeVerejnyOznamInfo);
        }))
    );
    publicNotices = noticeBatches.flat();
  }

  return buildResponse({
    capturedAt,
    searchRegime: "FULL_TEXT",
    query: { query: input.query },
    proceedings,
    publicNotices,
    requests,
    raw: { parsed: { proceedingPages: proceedingsPage.rawResults } }
  });
}

export async function searchReplikByPeriod(input: {
  dateFrom: string;
  dateTo: string;
  includeProceedings?: boolean;
  includeNotices?: boolean;
  pageSize?: number;
}): Promise<ReplikConnectorResponse> {
  const capturedAt = new Date().toISOString();
  const { konanie, oznam } = await getReplikClients("production");
  const pageSize = Math.min(input.pageSize ?? REPLIK_DEFAULTS.pageSize, 100);
  const requests: ReplikConnectorResponse["requests"] = [];

  let proceedings: NormalizedProceeding[] = [];
  let publicNotices: NormalizedPublicNotice[] = [];
  const rawParsed: Record<string, unknown> = {};

  if (input.includeProceedings !== false) {
    const proceedingsPage = await paginate<any>(async (page) => {
      const params = { DatumOd: input.dateFrom, DatumDo: input.dateTo, Stranka: page, VysledkovNaStranku: pageSize };
      const { result } = await callSoapOperation(konanie, "getKonaniePreObdobie", params);
      const items = pickList<any>(result, "KonanieInfoList", "KonanieInfo");
      requests.push({ service: "konanieService", operation: "getKonaniePreObdobie", params, rows: items.length, rawResponse: result });
      return { result, rows: items };
    });
    proceedings = proceedingsPage.rows.map(normalizeKonanieInfo);
    rawParsed.proceedingPages = proceedingsPage.rawResults;
  }

  if (input.includeNotices !== false) {
    const noticesPage = await paginate<any>(async (page) => {
      const params = { DatumOd: input.dateFrom, DatumDo: input.dateTo, Stranka: page, VysledkovNaStranku: pageSize };
      const { result } = await callSoapOperation(oznam, "getVerejneOznamyPreObdobie", params);
      const items = pickList<any>(result, "VerejnyOznamInfoList", "VerejnyOznamInfo");
      requests.push({ service: "oznamService", operation: "getVerejneOznamyPreObdobie", params, rows: items.length, rawResponse: result });
      return { result, rows: items };
    });
    publicNotices = noticesPage.rows.map(normalizeVerejnyOznamInfo);
    rawParsed.noticePages = noticesPage.rawResults;
  }

  return buildResponse({
    capturedAt,
    searchRegime: "PERIOD",
    query: { dateFrom: input.dateFrom, dateTo: input.dateTo },
    proceedings,
    publicNotices,
    requests,
    raw: { parsed: rawParsed }
  });
}

function buildResponse(input: {
  capturedAt: string;
  searchRegime: "ICO" | "FULL_TEXT" | "PERIOD";
  query: Record<string, string | null | undefined>;
  proceedings: NormalizedProceeding[];
  publicNotices: NormalizedPublicNotice[];
  requests: ReplikConnectorResponse["requests"];
  raw?: ReplikConnectorResponse["raw"];
}): ReplikConnectorResponse {
  const rows = input.proceedings.length + input.publicNotices.length;
  const highestSeverity = input.proceedings.some(p => p.uiSeverity === "critical")
    ? "critical"
    : input.proceedings.length || input.publicNotices.length
      ? "warning"
      : "none";

  return {
    capturedAt: input.capturedAt,
    connector: "replik",
    status: rows ? "queried" : "empty",
    rows,
    error: null,
    errorResponse: null,
    searchRegime: input.searchRegime,
    query: input.query,
    summary: {
      hasProceedings: input.proceedings.length > 0,
      proceedingsCount: input.proceedings.length,
      publicNoticesCount: input.publicNotices.length,
      highestSeverity,
      primaryFinding: rows ? "REPLIK records found." : "No REPLIK records found."
    },
    proceedings: input.proceedings,
    publicNotices: input.publicNotices,
    requests: input.requests,
    raw: input.raw
  };
}
```

## 11.9 Route/controller example

```ts
import { searchReplikByIco, searchReplikFullText, searchReplikByPeriod } from "../lib/connectors/replik/search";

export async function handleReplikSearch(req: any, res: any) {
  try {
    const { searchRegime } = req.body;

    if (searchRegime === "ICO") {
      const ico = String(req.body.ico ?? "").replace(/\D/g, "");
      if (!/^\d{8}$/.test(ico)) {
        return res.status(400).json({ error: "Invalid IČO. Expected 8 digits." });
      }
      return res.json(await searchReplikByIco({ ico, includeDetails: false }));
    }

    if (searchRegime === "FULL_TEXT") {
      const query = String(req.body.query ?? "").trim();
      if (query.length < 3) {
        return res.status(400).json({ error: "Query must contain at least 3 characters." });
      }
      return res.json(await searchReplikFullText({ query, includeRelatedNotices: true }));
    }

    if (searchRegime === "PERIOD") {
      const dateFrom = String(req.body.dateFrom ?? "");
      const dateTo = String(req.body.dateTo ?? "");
      if (!/^\d{4}-\d{2}-\d{2}$/.test(dateFrom) || !/^\d{4}-\d{2}-\d{2}$/.test(dateTo)) {
        return res.status(400).json({ error: "Dates must be in YYYY-MM-DD format." });
      }
      return res.json(await searchReplikByPeriod({ dateFrom, dateTo }));
    }

    return res.status(400).json({ error: "Unsupported REPLIK search regime." });
  } catch (err: any) {
    return res.status(502).json({
      connector: "replik",
      status: "error",
      error: err?.message ?? "REPLIK connector failed",
      errorResponse: err
    });
  }
}
```

---

## 12. Python verification script

Useful for smoke testing the API outside the app.

## 12.1 Install

```bash
pip install zeep lxml requests
```

## 12.2 Script

```python
from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session

KONANIE_WSDL = "https://replik-ws.justice.sk/ru-verejnost-ws/konanieService.wsdl"
OZNAM_WSDL = "https://replik-ws.justice.sk/ru-verejnost-ws/oznamService.wsdl"

session = Session()
transport = Transport(session=session, timeout=30)
settings = Settings(strict=False, xml_huge_tree=True)

konanie_client = Client(KONANIE_WSDL, transport=transport, settings=settings)
oznam_client = Client(OZNAM_WSDL, transport=transport, settings=settings)

ico = "34140469"

konania = konanie_client.service.getKonaniePodlaICO(
    Ico=ico,
    Stranka=0,
    VysledkovNaStranku=100,
    TypTriedenia="DatumPoslednejUdalosti",
)

print("Konania:")
print(konania)

oznamy = oznam_client.service.getVerejneOznamyPodlaICO(
    Ico=ico,
    Stranka=0,
    VysledkovNaStranku=100,
)

print("Oznamy:")
print(oznamy)
```

---

## 13. Error handling

## 13.1 Expected error categories

| Category | Example | App response |
|---|---|---|
| Validation error | invalid IČO, date format, empty query | HTTP 400 / user correction |
| SOAP fault | operation error returned by REPLIK | HTTP 502 / show “source temporarily unavailable” |
| Timeout | no response in 30 seconds | retry, then HTTP 504/502 |
| Parser error | unexpected XML shape | return raw data + log parser issue |
| Empty result | no proceedings/notices | status `empty`, not error |

## 13.2 Error response shape

```json
{
  "capturedAt": "2026-05-28T10:00:00.000Z",
  "connector": "replik",
  "status": "error",
  "rows": 0,
  "error": "REPLIK SOAP request failed: timeout",
  "errorResponse": {
    "operation": "getKonaniePodlaICO",
    "service": "konanieService"
  },
  "requests": []
}
```

---

## 14. Security and privacy

1. Use HTTPS only.
2. Do not expose raw SOAP errors directly to end users if they contain technical details.
3. Log request metadata, not unnecessary personal data.
4. Raw XML may contain personal data for natural persons; store only if needed and protect it like other screening/audit data.
5. Add retention rules for raw XML if the app stores historical search results.
6. Full-text mode can expose unrelated natural-person results; display a false-positive warning.

---

## 15. Recommended implementation phases

## Phase 1 — Connectivity and smoke tests

- Add WSDL configuration.
- Add SOAP clients.
- Test production IČO call.
- Test full-text call.
- Test period call.
- Confirm actual XML/JS object shape returned by selected library.

## Phase 2 — Normalization

- Implement `KonanieInfo` normalizer.
- Implement `VerejnyOznamInfo` normalizer.
- Implement date, IČO, whitespace and enum normalization.
- Persist raw parsed response for debugging.

## Phase 3 — UI integration

- Add three search regimes.
- Add summary card.
- Add proceeding cards.
- Add public notice timeline.
- Add raw source data section.
- Add SK/EN labels.

## Phase 4 — Performance and cache

- Add 24h query cache.
- Add pagination.
- Add throttling.
- Add timeouts and retries.
- Add operational logging.

## Phase 5 — Detail enrichment

- Add detail fetch buttons first.
- Later add automatic detail enrichment only for small result sets, e.g. ≤ 10 proceedings/notices.

---

## 16. Acceptance criteria

1. User can search by exact IČO.
2. User can search by full-text query.
3. User can search by date period.
4. The app displays proceedings and public notices separately.
5. The app displays a concise summary of whether REPLIK records were found.
6. The app preserves raw source data in a collapsible technical section.
7. The app handles empty results as a normal response.
8. The app does not fail if a list contains one item instead of an array.
9. The app does not request more than 100 records per page.
10. The app caches identical searches for 24h.
11. The app logs service, operation, parameters, response status and row count.
12. Full-text results are clearly marked as potentially imprecise.

---

## 17. Source references for developer

Official Ministry REPLIK manuals and API pages:

```text
REPLIK manuals page:
https://www.justice.gov.sk/sluzby/register-predinsolvencnych-likvidacnych-a-insolvencnych-konani/prirucky-a-manualy-k-is-replik/

Integration manual for public API, version 1.0.10:
https://www.justice.gov.sk/dokumenty/2026/04/Integracny-manual-pre-verejnost-API-verzia-1.0.10.pdf

Proceedings WSDL, production:
https://replik-ws.justice.sk/ru-verejnost-ws/konanieService.wsdl

Public notices WSDL, production:
https://replik-ws.justice.sk/ru-verejnost-ws/oznamService.wsdl

Proceedings examples:
https://www.justice.gov.sk/dokumenty/2025/09/examples-konania.txt

Public notices examples:
https://www.justice.gov.sk/dokumenty/2025/09/examples-verejneOznamy.txt
```

---

## 18. Developer note on exactness of SOAP XML

The safest implementation is a WSDL-generated client. The manual and examples define the operations, parameters and response fields, but SOAP libraries may expose slightly different object shapes after XML-to-JS/XML-to-Python conversion. Therefore:

- use operation names and parameter names exactly as documented,
- generate client bindings from WSDL,
- normalize single-object vs array responses,
- preserve raw XML during testing,
- add integration tests using official sample calls.


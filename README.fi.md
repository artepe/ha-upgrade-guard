# HA Upgrade Guard — suomeksi

**Selvitä, mikä muuttui Home Assistantin päivityksessä.** Työkalu ottaa Home Assistantista tilannekuvan ennen päivitystä, vertaa sitä uuteen tilanteeseen ja tekee offline-HTML-raportin.

- Kadonneet entiteetit
- Uudet `unavailable` / `unknown` -tilat
- Laitteiden toimintojen ja ominaisuuksien muutokset
- Uudet anturit sekä palautuneet entiteetit

Täysin paikallinen ja vain lukuoikeuksilla toimiva. Ei vaadi HACSia tai asennusta HAOS:n sisään. Tarvitset Python 3.10+:n ja Home Assistantin pitkäikäisen käyttöoikeustunnuksen.

## Asennus Macilla

Avaa projektikansio Terminalissa ja suorita:

```bash
export HA_URL="http://homeassistant.local:8123"
read -rs HA_TOKEN; export HA_TOKEN
# Liitä token ja paina Enter (syöte ei näy)
python3 guard.py snapshot --out before.json
```

Päivitä HA, odota järjestelmän ja integraatioiden käynnistymistä, ja aja:

```bash
python3 guard.py compare before.json --live --html report.html
open report.html
```

Testaa ilman Home Assistantia:

```bash
python3 guard.py compare examples/before.json examples/after.json --html demo.html
open demo.html
```

**Tietoturva:** Älä julkaise tokenia. Työkalu ei tallenna mittausarvoja eikä salasanoja, mutta entiteettien nimet voivat paljastaa tietoa kodistasi. Säilytä varsinaiset tilannekuvat yksityisinä.

Katso täydet käyttöohjeet englanninkielisestä [README.md](README.md)-tiedostosta.

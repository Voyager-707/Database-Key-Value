import os
from pathlib import Path
from hash_table import HashTable

# Serializuje operaci PUT do řádku logu:
# "PUT <delka_klice> <klic> <hodnota>\n"
# Délka klíče je potřeba proto, aby bylo možné při čtení
# přesně oddělit klíč od hodnoty, i kdyby uvnitř byly mezery

def encode_put(key,value):
    return f"PUT {len(key)} {key} {value}\n"

# Serializuje operaci DEL do řádku logu:
# "DEL <delka_klice> <klic>\n"

def encode_delete(key):
    return f"DEL {len(key)} {key}\n"

# Rozebere jeden řádek logu zpět na operaci.
# Vrací trojici (op, key, value), nebo None, pokud je řádek
# poškozený / neodpovídá formátu (např. useknutý kvůli
# selhání při zápisu na disk).

def decode_line(line):
    line = line.rstrip("\n")
    if not line:
        return None
    try:
        op,rest = line.split(" ",1)
    except ValueError:
        return None
    if op not in ("PUT","DEL"):
        return None
    try:
        key_len_str,rest = rest.split(" ",1)
        key_len = int(key_len_str)
    except(ValueError,AttributeError):
        return None
    if len(rest)< key_len:
        return None
    
    key = rest[:key_len]

    if op == "DEL":
        return("DEL",key,None)
    if len(rest) == key_len:
        value = ""
    elif rest[key_len] != " ":
        return None
    else:
        value = rest[key_len+1:]
    return("PUT",key,value)

class Database:

    # Konstruktor: uloží cestu k logovacímu souboru, vytvoří
    # prázdnou hash tabulku jako index v paměti a hned obnoví
    # data ze souboru voláním load()

    def __init__(self,filepath, initial_capacity = 16,max_load_factor=0.75):
        self.path = Path(filepath)
        self.index = HashTable(initial_capacity,max_load_factor)
        self.file = None
        self.load()

# file preparation 
    # Otevře logovací soubor v režimu přidávání ("a"), pokud
    # ještě není otevřený. Volá se líně, těsně před prvním zápisem

    def open_file(self):
        self.file= open(self.path, "a", encoding="utf-8") 

   # Připíše hotový řádek (už zakódovanou operaci) na konec
    # logovacího souboru a hned vyprázdní buffer (flush),
    # aby data nezmizela při neočekávaném ukončení programu.
    def append(self,line):
        if self.file is None or self.file.closed:
            self.open_file()
        self.file.write(line)
        self.file.flush()

    # Obnoví stav databáze při spuštění: řádek po řádku čte
    # logovací soubor a přehrává všechny operace PUT/DEL
    # v původním pořadí, čímž naplní hash tabulku index.
    # Poškozené řádky (decode_line vrátí None) se přeskočí.

    def load(self):
        if not self.path.exists():
            return
        with open( self.path, "r", encoding="utf-8") as fh:
            for raw_line in fh:
                parsed  = decode_line(raw_line)
                if parsed is None:
                    continue
            
                op,key,value = parsed
                if op == "PUT":
                    self.index.insert(key,value)
                elif op == "DEL":
                    self.index.delete(key)

 # "Úklid" logu: místo dlouhé historie všech operací
    # (včetně zastaralých PUT a smazaných klíčů) zapíše do
    # dočasného souboru jen aktuální obsah hash tabulky
    # a poté atomicky (os.replace) nahradí starý logovací
    # soubor novým, kompaktnějším.
    # Pokud něco selže, dočasný soubor se smaže a výjimka
    # se propaguje dál                   
    def compact(self):
        if self.file and not self.file.closed:
            self.file.close()
            self.file = None
        tmp_path = self.path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as tmp:
                for key, value in self.index.items():
                    tmp.write(encode_put(key, value))
            os.replace(tmp_path, self.path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise
###### key check
    # Ověří platnost klíče: musí to být neprázdný řetězec.
    # Pokud ne, vyhodí TypeError/ValueError.
    # Volá se na začátku všech veřejných metod.
    def validate_key(self,key):
        if not isinstance(key,str):
            raise TypeError(f"key must be str, got {type(key).__name__}")
        if not key:
            raise ValueError("key must not be empty")
##### Public API
# Uloží dvojici klíč-hodnota: nejdřív ověří klíč a hodnotu,
    # poté připíše operaci do logu (kvůli spolehlivosti)
    # a teprve pak aktualizuje index v paměti.

    def set(self,key,value):
        self.validate_key(key)
        if not isinstance(value,str):
            raise TypeError(f"value must be str, got {type(value).__name__}")
        self.append(encode_put(key,value))
        self.index.insert(key,value)

# Vrátí hodnotu podle klíče z indexu v paměti
    # (bez přístupu k souboru — index už obsahuje aktuální
    # stav po zavolání load())

    def get(self, key):
        self.validate_key(key)
        return self.index.get(key)
    
# Smaže klíč: pokud v indexu není, vrátí False a nic
    # neudělá. Pokud je, nejdřív zapíše operaci DEL do logu,
    # poté klíč odstraní z indexu a vrátí True

    def delete(self,key):
        self.validate_key(key)
        if not self.index.contains(key):
            return False
        self.append(encode_delete(key))
        self.index.delete(key)
        return True
    
# Zkontroluje, jestli klíč v databázi existuje (dotaz do indexu)

    def contains(self,key):
        self.validate_key(key)
        return self.index.contains(key)
    
 # Správně uzavře databázi: nejdřív zkompaktuje log (compact),
    # poté zavře souborový popisovač, pokud je ještě otevřený 
    #  
    def close(self):
        self.compact()
        if self.file and  not self.file.closed:
            self.file.close()
            self.file = None
        
    # Podpora konstrukce "with Database(...) as db:" —
    # při vstupu do bloku with vrátí sám objekt

    def __enter__(self):
        return self
    
   # Při opuštění bloku with (i při výjimce) automaticky
    # zavolá close(), aby se log zaručeně zkompaktoval
    # a soubor zavřel. 

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # Přehledná textová reprezentace objektu pro ladění:
    # ukazuje cestu k souboru, počet záznamů a samotný index.
    def __repr__(self):
        return (
            f"Database(path={str(self.path)!r}, "
            f"entries={self.index.size}, "
            f"index={self.index!r})"
        )


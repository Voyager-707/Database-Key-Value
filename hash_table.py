class Node:
    # Konstruktor uzlu spojového seznamu: uchovává klíč, hodnotu
    # a příznak "deleted" (logické smazání), přes které se ukládá
    # jedna dvojice klíč-hodnota v rámci jednoho bucketu
    def __init__(self,key,value):
        self.key = key
        self.value = value
        self.deleted = False
        self.next = None
            




class HashTable:
    # Konstruktor: nastaví počáteční kapacitu (počet bucketů)
    # a maximální load factor (poměr počtu prvků ku kapacitě,
    # po jehož překročení dojde k rehashi). Ověří, že obě
    # hodnoty jsou kladné, a vytvoří prázdné pole bucketů

    default_capacity = 16
    default_load_factor = 0.75
    def __init__(self,zacatecni_kapacita = default_capacity, max_load_factor = default_load_factor):
        if zacatecni_kapacita <= 0:
            raise ValueError("zacatecni kapacita musi byt kladna!!!")
        if max_load_factor <= 0:
            raise ValueError("Maximalni kapacita musi byt kladna!!!")
        self.capacity = zacatecni_kapacita
        self.max_load_factor= max_load_factor
        self.buckets = [None]*self.capacity
        self.size = 0 

# Spočítá hash klíče (řetězce) pomocí polynomiálního hashe
    # (Horner's method se základem 31), výsledek rovnou omezí
    # modulem aktuální kapacity.

    def hash_function(self,key):
        h = 0
        for char in key:
            h = (h * 31 + ord(char)) % self.capacity
        return h

     # Vrátí index bucketu, do kterého klíč patří.
    def bucket_index(self,key):
        return self.hash_function(key) %self.capacity

    # Zkontroluje, jestli by po vložení dalšího prvku load factor
    # překročil povolené maximum. Pokud ano, provede rehash:
    # zdvojnásobí kapacitu a přerozdělí všechny existující prvky
    # (kromě logicky smazaných, protože items() je nevrací)
    # do nového, většího pole bucketů
    def maybe_rehash(self):
        if(self.size+1)/self.capacity <= self.max_load_factor:
            return
        new_capacity = self.capacity*2
        new_buckets = [None]*new_capacity
        for key,value in self.items():
            h = self.hash_function(key) % new_capacity
            new_node = Node(key,value)
            new_node.next = new_buckets[h]
            new_buckets[h] = new_node

        self.buckets = new_buckets
        self.capacity = new_capacity

    # Projde všechny buckety a vrátí seznam dvojic (key, value)
    # pro všechny prvky, které nejsou logicky smazané.   
    def items(self):
        result=[]
        for bucket in self.buckets:
            node =bucket
            while node is not None:
                if not node.deleted:
                    result.append((node.key, node.value))
                node = node.next
        return result

    # Vloží nebo aktualizuje dvojici klíč-hodnota.
    # Nejdřív případně provede rehash. Pak projde spojový seznam
    # v příslušném bucketu: pokud klíč už existuje (i jako
    # logicky smazaný), jen aktualizuje hodnotu (a případně ho
    # "obnoví" zrušením příznaku deleted). Pokud klíč neexistuje,
    # vytvoří nový uzel na začátek seznamu v daném bucketu.

    def insert(self,key,value):
        self.maybe_rehash()
        index = self.bucket_index(key)
        node = self.buckets[index]

        while node is not None:
            if node.key == key:
                if node.deleted:
                    node.deleted = False
                    self.size+=1
                node.value = value
                return
            node = node.next 

        new_node = Node(key,value)
        new_node.next = self.buckets[index]
        self.buckets[index] = new_node
        self.size+=1
    # Vrátí hodnotu pro daný klíč, nebo None, pokud klíč
    # neexistuje nebo je logicky smazaný.
    def get(self,key):
        index = self.bucket_index(key)
        node = self.buckets[index]
        while node is not None:
            if node.key == key and not node.deleted:
                return node.value
            node = node.next
        return None
    
    # Logicky smaže klíč (nastaví příznak deleted na True,
    # uzel fyzicky neodstraňuje ze seznamu). Vrátí True, pokud
    # klíč existoval a byl smazán, jinak False.

    def delete(self,key):
        index = self.bucket_index(key)
        node = self.buckets[index]
        while node is not None:
            if node.key == key and not node.deleted:
                node.deleted = True
                self.size -= 1
                return True
            node = node.next
        return False
    # Zjistí, jestli klíč v tabulce existuje (a není smazaný)
    def contains(self,key):
        return self.get(key) is not None
    # Přehledná textová reprezentace objektu pro ladění:
    # ukazuje počet prvků, kapacitu a aktuální load factor.
    def __repr__(self):
        return (
            f"HashTable(size={self.size}, capacity={self.capacity}, "
            f"load_factor={self.size / self.capacity:.2f})"
        )
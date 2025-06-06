# Guide d'utilisation des images dans IntentLayer

## Structure des répertoires

Les images sont organisées dans les répertoires suivants :

```
static/images/
├── products/          # Images des produits
├── categories/        # Images des catégories
├── store/            # Images du magasin
└── support/          # Images du support
```

## Comment ajouter vos images

### 1. Placer les fichiers images

Copiez vos images dans les répertoires appropriés :

- **Produits** : `static/images/products/`
  - `iphone15-pro.jpg`
  - `samsung-galaxy-s24-ultra.jpg`
  - `macbook-air-m3.jpg`
  - `dell-xps-13.jpg`
  - `airpods-pro-2.jpg`
  - `apple-watch-series-9.jpg`
  - `wireless-charger.jpg`

- **Catégories** : `static/images/categories/`
  - `smartphones-collection.jpg`
  - `laptops-collection.jpg`
  - `accessories-collection.jpg`

- **Magasin** : `static/images/store/`
  - `boutique-interieur.jpg`

- **Support** : `static/images/support/`
  - `equipe-support.jpg`

### 2. Formats recommandés

- **Formats supportés** : JPG, PNG, WebP, SVG
- **Taille recommandée** : 800x600px pour les produits, 1200x800px pour les catégories
- **Poids** : < 500KB par image pour de meilleures performances

### 3. Configuration dans le catalogue

Les images sont référencées dans `data/knowledge/image_catalog.json`. Les URLs correspondent aux chemins :

```json
{
  "id": "smartphone_iphone15",
  "url": "/images/products/iphone15-pro.jpg",
  "alt": "iPhone 15 Pro en titane naturel",
  "description": "iPhone 15 Pro avec écran Super Retina XDR...",
  "keywords": ["iphone", "smartphone", "apple"]
}
```

### 4. Servir les images statiques

Pour que les images soient accessibles, vous devez configurer votre serveur web pour servir le répertoire `static/` :

#### Avec FastAPI (recommandé)

Ajoutez dans votre `main.py` :

```python
from fastapi.staticfiles import StaticFiles

app.mount("/images", StaticFiles(directory="static/images"), name="images")
```

#### Avec Nginx

```nginx
location /images/ {
    alias /path/to/intentlayer_aiserver/static/images/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 5. Ajouter de nouvelles images

Pour ajouter une nouvelle image :

1. **Placez le fichier** dans le bon répertoire
2. **Mettez à jour** `data/knowledge/image_catalog.json`
3. **Redémarrez le serveur** pour recharger le catalogue

Exemple d'ajout :

```json
{
  "id": "nouveau_produit",
  "url": "/images/products/nouveau-produit.jpg",
  "alt": "Description alternative",
  "description": "Description détaillée du produit",
  "keywords": ["mot-clé1", "mot-clé2", "mot-clé3"]
}
```

### 6. Optimisation des images

Pour de meilleures performances :

```bash
# Optimiser les JPG
jpegoptim --max=85 static/images/**/*.jpg

# Optimiser les PNG
optipng -o7 static/images/**/*.png

# Convertir en WebP (optionnel)
cwebp -q 85 input.jpg -o output.webp
```

## Fonctionnement du système

1. **Indexation** : Les images sont indexées dans ChromaDB via leurs descriptions et mots-clés
2. **Recherche** : Le système RAG trouve les images pertinentes selon le contexte
3. **Affichage** : Les images sont automatiquement ajoutées aux composants UI
4. **Contextualisation** : Les images apparaissent quand elles sont pertinentes à la conversation

## Dépannage

- **Image non trouvée** : Vérifiez le chemin dans `image_catalog.json`
- **Image non affichée** : Vérifiez la configuration du serveur statique
- **Mauvaise pertinence** : Améliorez les mots-clés et descriptions
- **Performance lente** : Optimisez la taille des images
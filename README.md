# Agent IA — Restauration de photos via WhatsApp

## Structure du projet

```
photo-restoration-bot/
├── app.py           → Bot WhatsApp (Flask + webhooks Meta)
├── restoration.py   → Pipeline IA (GFPGAN + Real-ESRGAN)
├── requirements.txt → Dépendances Python
├── Procfile         → Config Railway/Render
└── models/          → Modèles IA (créé automatiquement)
```

## Étapes de déploiement

### 1. Créer le compte Meta Business API

1. Aller sur https://developers.facebook.com
2. Créer une app → choisir "Business"
3. Ajouter le produit "WhatsApp"
4. Récupérer :
   - `WHATSAPP_TOKEN` (token temporaire d'accès)
   - `PHONE_NUMBER_ID` (ID du numéro de test)

### 2. Déployer sur Railway (gratuit)

1. Créer un compte sur https://railway.app
2. "New Project" → "Deploy from GitHub"
3. Pousser ce dossier sur GitHub d'abord
4. Ajouter les variables d'environnement dans Railway :

```
WHATSAPP_TOKEN=ton_token_meta
PHONE_NUMBER_ID=ton_phone_number_id
VERIFY_TOKEN=mon_token_secret
```

5. Railway te donne une URL publique, ex : `https://ton-bot.railway.app`

### 3. Configurer le webhook Meta

Dans le dashboard Meta :
- Webhook URL : `https://ton-bot.railway.app/webhook`
- Verify Token : `mon_token_secret`
- S'abonner à : `messages`

### 4. Activer les modèles IA complets

Dans `requirements.txt`, décommenter les lignes :
```
gfpgan>=1.3.8
realesrgan>=0.3.0
basicsr>=1.4.2
facexlib>=0.3.0
```

Puis redéployer. Les modèles (~350 Mo) se téléchargent automatiquement.

## Test local

```bash
pip install -r requirements.txt
python app.py
# Bot accessible sur http://localhost:5000
```

Pour tester le webhook localement, utiliser ngrok :
```bash
ngrok http 5000
# Copier l'URL https dans le dashboard Meta
```

## Variables d'environnement

| Variable | Description |
|---|---|
| `WHATSAPP_TOKEN` | Token d'accès Meta (permanent après config) |
| `PHONE_NUMBER_ID` | ID du numéro WhatsApp Business |
| `VERIFY_TOKEN` | Token de vérification webhook (choisis toi-même) |
| `PORT` | Port du serveur (5000 par défaut) |

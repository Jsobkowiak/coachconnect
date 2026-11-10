"""Prepare a private, one-use recovery link without printing the recovery secret."""
from pathlib import Path
import hashlib,secrets,os,re
root=Path(__file__).resolve().parent.parent
private=root/'.local/training-auth';private.mkdir(parents=True,exist_ok=True)
secret=private/'owner-token'
if not secret.exists():secret.write_text(secrets.token_urlsafe(32))
os.chmod(secret,0o600)
token=secret.read_text().strip();digest=hashlib.sha256(token.encode()).hexdigest().upper()
env=root/'.env';text=env.read_text() if env.exists() else ''
line='TRAINING_BOOTSTRAP_TOKEN_HASH='+digest
text=re.sub(r'^TRAINING_BOOTSTRAP_TOKEN_HASH=.*$',line,text,flags=re.M) if re.search(r'^TRAINING_BOOTSTRAP_TOKEN_HASH=',text,re.M) else text.rstrip()+'\n'+line+'\n'
env.write_text(text)
(private/'initialisation.url').write_text('http://localhost:8081/#initialisation='+token)
os.chmod(private/'initialisation.url',0o600)
print('Récupération locale préparée ; lien privé dans .local/training-auth/initialisation.url.')

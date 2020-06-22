# Configuration d'une DEBIAN

## Partager un disque en NFS
### Coté Serveur

> les variables entre <...> sont à remplacer en fonction de votre configuration

```sudo apt install nfs-server```

```sudo nano /etc/fstab```
> ```/dev/disk/by-uuid/<uuid du disque>  </mnt/sandisk> auto nosuid,nodev,nofail,x-gvfs-show 0 0```

> ```<uuid du disque>``` 62b3a146-fe89-4d05-bd46-6433b3053e75 par exemple

```sudo nano /etc/exports ```
> ```</mnt/sandisk/nas> *(rw,no_root_squash,insecure,sync,no_subtree_check)```

> ```</mnt/sandisk/nas>``` nom de la ressource sur le réseau

### Coté Client

```sudo nano /etc/fstab ```
> ```<192.168.0.76>:</mnt/sandisk/nas> </mnt/nas> nfs auto,nofail,noatime,nolock,intr,tcp,actimeo=1800 0 0```

> ```<192.168.0.76>``` n° ip du serveur

> ```</mnt/sandisk/nas>``` nom de la ressource sur le serveur

> ```</mnt/nas>``` nom du montage sur la machine cliente


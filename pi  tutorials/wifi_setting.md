# see wifi list on wlan1
```
nmcli dev wifi list ifname wlan1
```

# connect to wifi in wlan1 interface
``` semi- work:
sudo nmcli dev wifi connect "TELLO-9B58FC" ifname wlan1
```
``` 
sudo nmcli dev wifi connect "TELLO-9C5CC3" ifname wlan1
```
``` work
sudo nmcli dev wifi connect "TELLO-9B4CBE" ifname wlan1
```

# disconnect from wifi wlan1 interface
```
sudo nmcli dev disconnect wlan1
```

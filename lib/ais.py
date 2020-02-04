import bitstring
import LatLon


#ais NMEA payload encoding
payloadencoding = {0:'0',1:'1',2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',8:'8',9:'9',10:'.',11:',',12:'<',13:'=',14:'>',15:'?',16:'@',17:'A',18:'B',19:'C',20:'D',21:'E',22:'F',23:'G',24:'H',25:'I',26:'J',27:'K',28:'L',29:'M',30:'N',31:'O',32:'P',33:'Q',34:'R',35:'S',36:'T',37:'U',38:'V',39:'W',40:"`",41:'a',42:'b',43:'c',44:'d',45:'e',46:'f',47:'g',48:'h',49:'i',50:'j',51:'k',52:'l',53:'m',54:'n',55:'o',56:'p',57:'q',58:'r',59:'s',60:'t',61:'u',62:'v',63:'w'}
# create AIS-string decoding map
reverseencoding = dict()

for k,e in payloadencoding.iteritems():
    reverseencoding[e] = k

def unpackbitstream(bits168): #bitstream -> AIS payload map
    payload = dict()

    typ = bits168[0:6]
    rep = bits168[6:8]
    mmsi = bits168[8:38]
    stat = bits168[38:42]
    rot = bits168[42:50]
    sog = bits168[50:60]
    pa = bits168[60:61]
    lon = bits168[61:89]
    lat = bits168[89:116]
    cog = bits168[116:128]
    hdg = bits168[128:137]
    ts = bits168[137:143]
    mi = bits168[143:145]
    spare = bits168[145:148]
    raim = bits168[148:149]
    radio = bits168[149:168]

    payload['type'] = typ
    payload['repeat'] = rep
    payload['mmsi'] = mmsi
    payload['status'] = stat
    payload['turn'] = rot
    payload['speed'] = sog
    payload['accuracy'] = pa
    payload['lon'] = lon
    payload['lat'] = lat
    payload['course'] = cog
    payload['heading'] = hdg
    payload['second'] = ts
    payload['maneuver'] = mi
    payload['spare'] = spare
    payload['raim'] = raim
    payload['radio'] = radio

    return payload

def nmeaChecksum(s): # str -> two hex digits in str
    chkSum = 0
    subStr = s[1:len(s)]

    for e in range(len(subStr)):
        chkSum ^= ord((subStr[e]))

    hexstr = str(hex(chkSum))[2:4]
    if len(hexstr) == 2:
        return hexstr
    else:
        return '0'+hexstr

# join NMEA pre- and postfix to payload string
def joinNMEAstrs(payloadstr): #str -> str
    tempstr = '!AIVDM,1,1,,A,' + payloadstr + ',0'
    chksum = nmeaChecksum(tempstr)
    tempstr += '*'
    tempstr += chksum
    return tempstr

# encode bitstream to 6bit ascii string
def aisencode (aisstr): #BitString -> string
    l = 0
    r = 6 # six bit chunks
    aisnmea = []

    for i in range (0,28): #168 bits in 28 chunks of 6
        chunk1 = aisstr[l:r]
        char = str(chunk1.uint)
        intie = int(char)
        aisnmea.append(payloadencoding[intie])
        l += 6
        r +=6

    aisstr = ''.join(aisnmea)
    return aisstr

def bin6(x): # int -> 6 binary digits
    return ''.join(x & (1 << i) and '1' or '0' for i in range(5,-1,-1))

# convert vector of ints to bitstring
def intvec2bitstring(aisvec): #intvec -> Bitstring
    nmeanums = []

    for i in range(len(aisvec)):
        nmeanums.append(bin6(aisvec[i]))
        bitstring = ''.join(nmeanums)
    return bitstring

# decode AIS string to int vector
def aisdecode(aisstr): #string -> numvec
    numvec = []
    numstr = ''

    for i in aisstr:
        key = i
        code = reverseencoding[key]
        numvec.append(code)
    return numvec

# create a map with all AIS elements as keys
def pack(packmap, type, repeat,mmsi,status,turn,speed,accuracy,lon,lat,course,heading,second,maneuver,spare,raim,radio): #map,normal ints -> packmap
    packmap['type'] = bitstring.BitString(uint=type,length=6)
    packmap['repeat'] = bitstring.BitString(uint=repeat,length=2)
    packmap['mmsi'] = bitstring.BitString(uint=mmsi,length=30)
    packmap['status'] = bitstring.BitString(uint=status,length=4)
    packmap['turn'] = bitstring.BitString(uint=turn,length=8)
    packmap['speed'] = bitstring.BitString(uint=speed,length=10)
    packmap['accuracy'] = bitstring.BitString(uint=accuracy,length=1)
    packmap['lon'] = bitstring.BitString(uint=lon,length=28)
    packmap['lat'] = bitstring.BitString(uint=lat,length=27)
    packmap['course'] = bitstring.BitString(uint=course,length=12)
    packmap['heading'] = bitstring.BitString(uint=heading,length=9)
    packmap['second'] = bitstring.BitString(uint=second,length=6)
    packmap['maneuver'] = bitstring.BitString(uint=maneuver,length=2)
    packmap['spare'] = bitstring.BitString(uint=spare,length=3)
    packmap['raim'] = bitstring.BitString(uint=raim,length=1)
    packmap['radio'] = bitstring.BitString(uint=radio,length=19)

    return packmap

# create a bitstring from a map
def unpack(packmap): #map -> bitstring
    bitstr =bitstring.BitString = packmap['type']
    bitstr.append(packmap['repeat'])
    bitstr.append(packmap['mmsi'])
    bitstr.append(packmap['status'])
    bitstr.append(packmap['turn'])
    bitstr.append(packmap['speed'])
    bitstr.append(packmap['accuracy'])
    bitstr.append(packmap['lon'])
    bitstr.append(packmap['lat'])
    bitstr.append(packmap['course'])
    bitstr.append(packmap['heading'])
    bitstr.append(packmap['second'])
    bitstr.append(packmap['maneuver'])
    bitstr.append(packmap['spare'])
    bitstr.append(packmap['raim'])
    bitstr.append(packmap['radio'])
    return bitstr

#Convert coordinates to something understandable by pack
def lat_lon(lat,emis,lon,emis2):
    lat_deg = lat[:2]
    lat_min = lat[2:]
    lon_deg = lon[:3]
    lon_min = lon[3:]
    coords = LatLon.string2latlon(lat_deg + ' ' + lat_min + ' ' + emis, lon_deg + ' ' + lon_min + ' ' + emis2, 'd% %m% %H')
    res= coords.to_string('D%')
    res_lat = int(float(res[0])*600000)
    res_lon = int(float(res[1])*600000)
    print(str(res_lat) + ' ' + str(res_lon))
    res_coords = res_lat, res_lon 
    return res_coords

def AIS_format(data):         
    #let's try here to change data
    NMEA = data.split(',')
    if NMEA[0] == "$GPGLL":
        lat = NMEA[1]
        lat2 = NMEA[2]
        lon = NMEA[3]
        lon2 = NMEA[4]
        time = NMEA[5]
        formatted =  "At " + time[:2] + ":" + time[2:4] + ":" + time[4:6] + " we are in " + lat[:2] + " " + lat[2:] + " " + lat2 + " " + lon[1:3] + " " + lon[3:] + " " + lon2 + '\n'
        coords = lat_lon(NMEA[1],NMEA[2],NMEA[3],NMEA[4],)
        #newmap = dict()
        newmap = pack(dict(),1,0,123456,1,12,30,1,coords[1],coords[0],900,89,59,1,0,0,0)
        newstream = unpack(newmap)
        newencode = aisencode(newstream)
        result = joinNMEAstrs(newencode)
        return result

import requests
import sys
import json
import datetime


class deovr:
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1"
    }
    domain='stash.home'

    url_prefix='http://'+domain
    # In deovr, we are adding the lists: VR and 2D
    # You can add a string for studio or performers you want to add as lists in deovr
    # pinned_studio=['Wankz VR']
    pinned_studio=[]
    pinned_performers=[]

    def __init__(self, url):
        self.url = url

        self.path='/root/.stash/deovr/'



    def __callGraphQL(self, query, variables=None):
        json = {}
        json['query'] = query
        if variables != None:
            json['variables'] = variables

        # handle cookies
        response = requests.post(self.url, json=json, headers=self.headers)

        if response.status_code == 200:
            result = response.json()
            if result.get("error", None):
                for error in result["error"]["errors"]:
                    raise Exception("GraphQL error: {}".format(error))
            if result.get("data", None):
                return result.get("data")
        else:
            raise Exception(
                "GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(response.status_code, response.content,
                                                                                query, variables))

    def get_scenes_with_tag(self, tag):
        tagID = self.findTagIdWithName(tag)
        query = """query findScenes($scene_filter: SceneFilterType!) {
  findScenes(scene_filter: $scene_filter filter: {sort: "date",direction: DESC,per_page: -1} ) {
    count
    scenes {
      id
      checksum
      oshash
      title
      details
      url
      date
      rating
      organized
      o_counter
      path
      file {
        size
        duration
        video_codec
        audio_codec
        width
        height
        framerate
        bitrate
      }
      paths {
        screenshot
        preview
        stream
        webp
        vtt
        chapters_vtt
        sprite
        funscript
      }
      galleries {
        id
        checksum
        path
        title
        url
        date
        details
        rating
        organized
        studio {
          id
          name
          url
        }
        image_count
        tags {
          id
          name
          image_path
          scene_count
        }
      }
      performers {
        id
        name
        gender
        url
        twitter
        instagram
        birthdate
        ethnicity
        country
        eye_color
        country
        height
        measurements
        fake_tits
        career_length
        tattoos
        piercings
        aliases
      }
      studio{
        id
        name
        url
        stash_ids{
          endpoint
          stash_id
        }
      }
    tags{
        id
        name
      }

      stash_ids{
        endpoint
        stash_id
      }
    }
  }
}"""

        variables = {"scene_filter": {"tags": {"value": [tagID], "modifier": "INCLUDES"}}}
        result = self.__callGraphQL(query, variables)
        return result["findScenes"]["scenes"]

    def createTagWithName(self, name):
        query = """
mutation tagCreate($input:TagCreateInput!) {
  tagCreate(input: $input){
    id       
  }
}
"""
        variables = {'input': {
            'name': name
        }}

        result = self.__callGraphQL(query, variables)
        return result["tagCreate"]["id"]

    def findTagIdWithName(self, name):
        query = """query {
  allTags {
    id
    name
  }
}"""

        result = self.__callGraphQL(query)

        for tag in result["allTags"]:
            if tag["name"] == name:
                return tag["id"]
        return None

    def setup(self):
        tags=["VR","SBS","TB","export_deovr","FLAT","DOME","SPHERE","FISHEYE","MKX200"]
        for t in tags:
            tag = self.findTagIdWithName(t)
            if tag is None:
                self.createTagWithName(t)

    def run(self):
        scenes = self.get_scenes_with_tag("export_deovr")
        data = {}
        index = 1

        if scenes is not None:
            recent=[]
            vr=[]
            flat=[]
            studio_cache={}
            performer_cache={}
            for s in scenes:
                r={}
                r["title"] = s["title"]
                r["videoLength"]=int(s["file"]["duration"])
                url=s["paths"]["screenshot"]
                r["thumbnailUrl"] =self.url_prefix+url[21:]
                r["video_url"]=self.url_prefix+'/custom/deovr/'+s["id"]+'.json'
                recent.append(r)

                if "180_180x180_3dh_LR" in s["path"]:
                    vr.append(r)
                elif [x for x in ['DOME','SPHERE','FISHEYE','MKX200','VR'] if x in  [x["name"] for x in s["tags"]]]:
                    vr.append(r)
                else:
                    flat.append(r)

                scene={}
                scene["id"]=s["id"]
                scene["title"]=s["title"]
                scene["authorized"]=1
                scene["description"]=s["details"]
                if "studio" in s and s["studio"] is not None:
                    scene["paysite"]={"id": 1,"name": s["studio"]["name"],"is3rdParty": True}
                    if s["studio"]["name"] in studio_cache:
                        studio_cache[s["studio"]["name"]].append(r)
                    else:
                        studio_cache[s["studio"]["name"]]=[r]
                scene["thumbnailUrl"]=s["paths"]["screenshot"]
                url= s["paths"]["screenshot"]
                scene["thumbnailUrl"] =self.url_prefix+url[21:]
                scene["isFavorite"]= False
                scene["isScripted"]= False
                scene["isWatchlist"]= False

                vs={}
                vs["resolution"]=s["file"]["height"]
                vs["height"]=s["file"]["height"]
                vs["width"]=s["file"]["width"]
                vs["size"]=s["file"]["size"]
                url=s["paths"]["stream"]
                vs["url"]=self.url_prefix+url[21:]
                scene["encodings"]=[{"name":s["file"]["video_codec"],"videoSources":[vs]}]


                if "180_180x180_3dh_LR" in s["path"]:
                    scene["is3d"] = True
                    scene["screenType"]="dome"
                    scene["stereoMode"]="sbs"
                else:
                    scene["screenType"]="flat"
                    scene["is3d"]=False
                if 'SBS' in [x["name"] for x in s["tags"]]:
                    scene["stereoMode"] = "sbs"
                elif 'TB' in [x["name"] for x in s["tags"]]:
                    scene["stereoMode"] = "tb"

                if 'FLAT' in [x["name"] for x in s["tags"]]:
                    scene["screenType"]="flat"
                    scene["is3d"]=False
                elif 'DOME' in [x["name"] for x in s["tags"]]:
                    scene["is3d"] = True
                    scene["screenType"]="dome"
                elif 'SPHERE' in [x["name"] for x in s["tags"]]:
                    scene["is3d"] = True
                    scene["screenType"]="sphere"
                elif 'FISHEYE' in [x["name"] for x in s["tags"]]:
                    scene["is3d"] = True
                    scene["screenType"]="fisheye"
                elif 'MKX200' in [x["name"] for x in s["tags"]]:
                    scene["is3d"] = True
                    scene["screenType"]="mkx200"

                scene["timeStamps"]=None

                actors=[]
                for p in s["performers"]:
                    #actors.append({"id":p["id"],"name":p["name"]})
                    actors.append({"id": p["id"], "name": p["name"]})
                scene["actors"]=actors

                for p in self.pinned_performers:
#                    print([x["name"] for x in s["performers"]])
                    if p.lower() in [x["name"].lower() for x in s["performers"]]:
                        if p in performer_cache:
                            performer_cache[p].append(r)
                        else:
                            performer_cache[p]=[r]

                scene["fullVideoReady"]= True
                scene["fullAccess"]= True

                with open(self.path+s["id"]+'.json', 'w') as outfile:
                    json.dump(scene, outfile)
                    outfile.close()


            data["scenes"]=[{"name":"Recent","list":recent},{"name":"VR","list":vr},{"name":"2D","list":flat}]
            for sn in self.pinned_studio:
                if sn in studio_cache:
                    data["scenes"].append({"name":sn,"list":studio_cache[sn]})
            for pn in self.pinned_performers:
                if pn in performer_cache:
                    data["scenes"].append({"name":pn,"list":performer_cache[pn]})


        with open(self.path+"deovr.json", 'w') as outfile:
            json.dump(data, outfile)
            outfile.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        url = "http://localhost:9999/graphql"
        if len(sys.argv) > 2:
            url = sys.argv[2]

        if sys.argv[1] == "setup":
            client = deovr(url)
            client.setup()

        elif sys.argv[1] =="json":
            client = deovr(url)
            client.setup()
            client.run()
        elif sys.argv[1]== "api":
            fragment = json.loads(sys.stdin.read())
            scheme=fragment["server_connection"]["Scheme"]
            port=fragment["server_connection"]["Port"]
            domain="localhost"
            if "Domain" in fragment["server_connection"]:
                domain = fragment["server_connection"]["Domain"]
            if not domain:
                domain='localhost'
            url = scheme + "://" + domain + ":" +str(port) + "/graphql"
            client = deovr(url)
            mode=fragment["args"]["mode"]
#            client.debug("Mode: "+mode)
            if mode == "setup":
                client.setup()
            elif mode == "json":
                client.run()

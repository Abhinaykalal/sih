"""
inject_leaf_ai.py - Injects LeafAIScreen into the APK bundle and wires it to navigation.
"""
import os
import re

EXTRACTED_DIR = r"F:\sih\vaibhav_apk_extracted"
BUNDLE_PATH = os.path.join(EXTRACTED_DIR, "assets", "index.android.bundle")

# ── LeafAI Screen module ──────────────────────────────────────────────────────
LEAF_AI_MODULE = """__d(function(g,_r,_i,_a,m,_e,d){'use strict';
var React=_r(d[0]),RN=_r(d[1]);
var u=React.createElement;
var CROPS=['Rice','Wheat','Maize','Tomato','Potato','Cotton','Soybean','Sugarcane','Bajra','Jowar'];
var API_BASE='https://agrisaathi-6dg1.onrender.com';

function LeafAIScreen(props){
  var goBack=props.onBack||function(){};
  var _s0=React.useState(null),imgData=_s0[0],setImgData=_s0[1];
  var _s1=React.useState(null),imgUri=_s1[0],setImgUri=_s1[1];
  var _s2=React.useState(false),loading=_s2[0],setLoading=_s2[1];
  var _s3=React.useState(null),result=_s3[0],setResult=_s3[1];
  var _s4=React.useState(null),errMsg=_s4[0],setErrMsg=_s4[1];
  var _s5=React.useState('Rice'),crop=_s5[0],setCrop=_s5[1];

  function pickImage(){
    setResult(null);setErrMsg(null);
    RN.Alert.alert('Select Image','Choose source',[
      {text:'Camera',onPress:openCamera},
      {text:'Gallery',onPress:openGallery},
      {text:'Cancel',style:'cancel'}
    ]);
  }

  function tryImagePicker(fn){
    try{
      var ImagePicker=_r(d[2]);
      fn(ImagePicker);
    }catch(e){
      setErrMsg('Image picker unavailable: '+e.message+'. Please use a native build.');
    }
  }

  function openCamera(){
    tryImagePicker(function(IP){
      IP.launchCamera({mediaType:'photo',includeBase64:true,quality:0.8,maxWidth:800,maxHeight:800},handlePick);
    });
  }

  function openGallery(){
    tryImagePicker(function(IP){
      IP.launchImageLibrary({mediaType:'photo',includeBase64:true,quality:0.8,maxWidth:800,maxHeight:800},handlePick);
    });
  }

  function handlePick(r){
    if(!r||r.didCancel||r.errorCode)return;
    var asset=r.assets&&r.assets[0];
    if(!asset)return;
    setImgUri(asset.uri||null);
    setImgData(asset.base64||null);
    setResult(null);setErrMsg(null);
  }

  function analyze(){
    if(!imgData){setErrMsg('Please select a leaf photo first.');return;}
    setLoading(true);setErrMsg(null);setResult(null);
    var body=JSON.stringify({image_base64:imgData,crop_type:crop});
    fetch(API_BASE+'/api/vision-diagnose',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:body
    }).then(function(r){return r.json();}).then(function(data){
      setResult(data);setLoading(false);
    }).catch(function(e){
      setErrMsg('Network error: '+e.message);setLoading(false);
    });
  }

  var C={
    container:{flex:1,backgroundColor:'#F0FDF4'},
    hdr:{backgroundColor:'#15803D',padding:18,paddingTop:30,flexDirection:'row',alignItems:'center'},
    hdrBack:{color:'#fff',fontSize:20,fontWeight:'700',paddingRight:12},
    hdrTitle:{color:'#fff',fontSize:19,fontWeight:'800'},
    body:{padding:16,paddingBottom:60},
    lbl:{fontSize:13,fontWeight:'700',color:'#166534',marginTop:16,marginBottom:6},
    cropRow:{flexDirection:'row',flexWrap:'wrap'},
    chip:{paddingHorizontal:12,paddingVertical:6,borderRadius:20,borderWidth:1,borderColor:'#D1FAE5',backgroundColor:'#fff',margin:3},
    chipSel:{backgroundColor:'#15803D',borderColor:'#15803D'},
    chipTxt:{fontSize:12,fontWeight:'600',color:'#374151'},
    chipTxtSel:{color:'#fff'},
    pickBtn:{backgroundColor:'#fff',borderRadius:14,borderWidth:2,borderColor:'#15803D',borderStyle:'dashed',padding:22,alignItems:'center',marginTop:6},
    pickIco:{fontSize:40},
    pickTxt:{color:'#15803D',fontSize:13,fontWeight:'700',marginTop:6,textAlign:'center'},
    imgPreview:{width:'100%',height:210,borderRadius:14,marginTop:10,resizeMode:'cover'},
    analyzeBtn:{backgroundColor:'#15803D',borderRadius:12,padding:16,alignItems:'center',marginTop:14},
    analyzeBtnDis:{backgroundColor:'#9CA3AF'},
    analyzeTxt:{color:'#fff',fontSize:15,fontWeight:'800'},
    loaderRow:{alignItems:'center',marginTop:16},
    loaderTxt:{color:'#15803D',fontSize:13,fontWeight:'600',marginTop:8},
    errBox:{backgroundColor:'#FEE2E2',borderRadius:10,padding:12,marginTop:10},
    errTxt:{color:'#991B1B',fontSize:13},
    card:{backgroundColor:'#fff',borderRadius:14,padding:16,marginTop:14,borderWidth:1,borderColor:'#D1FAE5'},
    cardTag:{fontSize:10,fontWeight:'700',color:'#15803D',letterSpacing:1,textTransform:'uppercase',marginBottom:4},
    cardTitle:{fontSize:19,fontWeight:'800',color:'#1F2937',marginBottom:8},
    confLbl:{fontSize:12,color:'#6B7280',marginBottom:4},
    confBar:{height:8,borderRadius:4,backgroundColor:'#DCFCE7',overflow:'hidden',marginBottom:12},
    confFill:{height:8,borderRadius:4,backgroundColor:'#15803D'},
    actionHdr:{fontSize:13,fontWeight:'700',color:'#374151',marginBottom:3},
    actionTxt:{fontSize:12,color:'#6B7280',lineHeight:18},
    warnTxt:{fontSize:11,color:'#F59E0B',marginTop:8,fontStyle:'italic'},
    noResultTtl:{fontSize:15,fontWeight:'700',color:'#374151',marginBottom:4},
    noResultTxt:{fontSize:12,color:'#6B7280'},
    unavailBox:{backgroundColor:'#FEF3C7',borderRadius:10,padding:14},
    unavailTtl:{fontSize:13,fontWeight:'700',color:'#92400E',marginBottom:3},
    unavailTxt:{fontSize:12,color:'#78350F'}
  };

  function renderResult(){
    if(!result)return null;
    var s=result.status;
    if(s==='EXPERIMENTAL_PREDICTION'){
      var pct=result.confidence_pct||0;
      return u(RN.View,{style:C.card},
        u(RN.Text,{style:C.cardTag},'Leaf AI — Diagnosis'),
        u(RN.Text,{style:C.cardTitle},result.diagnosis||'Unknown'),
        u(RN.Text,{style:C.confLbl},'Confidence: '+pct+'%'),
        u(RN.View,{style:C.confBar},u(RN.View,{style:[C.confFill,{width:Math.min(pct,100)+'%'}]})),
        u(RN.Text,{style:C.actionHdr},'Recommended Action'),
        u(RN.Text,{style:C.actionTxt},result.action||'Consult an agronomist.'),
        result.warning?u(RN.Text,{style:C.warnTxt},'\\u26a0 '+result.warning):null
      );
    }
    if(s==='NO_RELIABLE_RESULT'){
      return u(RN.View,{style:C.card},
        u(RN.Text,{style:C.noResultTtl},'Low Confidence — Retake Photo'),
        u(RN.Text,{style:C.noResultTxt},result.action||'Ensure the leaf fills the frame clearly, in good lighting.')
      );
    }
    if(s==='NOT_A_LEAF'){
      return u(RN.View,{style:C.card},
        u(RN.Text,{style:C.noResultTtl},'No Leaf Detected'),
        u(RN.Text,{style:C.noResultTxt},'Please take a close-up photo of a crop leaf on a plain background.')
      );
    }
    if(s==='MODEL_UNAVAILABLE'||s==='MODEL_INCOMPATIBLE'){
      return u(RN.View,{style:[C.card,C.unavailBox]},
        u(RN.Text,{style:C.unavailTtl},'Vision Model Unavailable'),
        u(RN.Text,{style:C.unavailTxt},result.action||'The leaf disease model is not currently deployed on the server.')
      );
    }
    return u(RN.View,{style:C.card},
      u(RN.Text,{style:C.noResultTtl},'Status: '+s),
      u(RN.Text,{style:C.noResultTxt},(result.action||result.reason)||'No diagnosis available.')
    );
  }

  return u(RN.View,{style:C.container},
    u(RN.View,{style:C.hdr},
      u(RN.TouchableOpacity,{onPress:goBack},u(RN.Text,{style:C.hdrBack},'\\u2190')),
      u(RN.Text,{style:C.hdrTitle},'\\uD83C\\uDF3F Leaf AI \\u2014 Disease Scan')
    ),
    u(RN.ScrollView,{contentContainerStyle:C.body},
      u(RN.Text,{style:C.lbl},'1. Select Your Crop'),
      u(RN.View,{style:C.cropRow},
        CROPS.map(function(c){
          return u(RN.TouchableOpacity,{key:c,style:[C.chip,crop===c&&C.chipSel],onPress:function(){setCrop(c);}},
            u(RN.Text,{style:[C.chipTxt,crop===c&&C.chipTxtSel]},c)
          );
        })
      ),
      u(RN.Text,{style:C.lbl},'2. Capture or Upload Leaf Photo'),
      u(RN.TouchableOpacity,{style:C.pickBtn,onPress:pickImage},
        imgUri
          ? u(RN.Image,{source:{uri:imgUri},style:C.imgPreview})
          : u(RN.View,{style:{alignItems:'center'}},
              u(RN.Text,{style:C.pickIco},'\\uD83D\\uDCF7'),
              u(RN.Text,{style:C.pickTxt},'Tap to take a photo\\nor upload from gallery')
            )
      ),
      imgUri&&u(RN.TouchableOpacity,{onPress:pickImage},
        u(RN.Text,{style:{color:'#15803D',fontSize:12,textAlign:'center',marginTop:6,fontWeight:'600'}},'Change photo')
      ),
      u(RN.TouchableOpacity,{
        style:[C.analyzeBtn,(!imgData||loading)&&C.analyzeBtnDis],
        onPress:analyze,
        disabled:!imgData||loading
      },
        loading
          ? u(RN.ActivityIndicator,{color:'#fff'})
          : u(RN.Text,{style:C.analyzeTxt},'\\uD83D\\uDD2C Analyze Leaf')
      ),
      loading&&u(RN.View,{style:C.loaderRow},u(RN.Text,{style:C.loaderTxt},'Running vision model analysis\\u2026')),
      errMsg&&u(RN.View,{style:C.errBox},u(RN.Text,{style:C.errTxt},'\\u26a0 '+errMsg)),
      renderResult(),
      u(RN.View,{style:{height:40}})
    )
  );
}

_e.LeafAIScreen=LeafAIScreen;
},9999,[1,46,292]);"""
# Note: d[2]=292 is react-native-image-picker (or we handle the error gracefully)


def main():
    print("Reading bundle...")
    with open(BUNDLE_PATH, "r", encoding="utf-8") as f:
        bundle = f.read()

    original_size = len(bundle)

    # ── 1. Inject LeafAI module ───────────────────────────────────────────────
    if "LeafAIScreen" in bundle:
        print("  LeafAIScreen already present in bundle, skipping injection.")
    else:
        print("  Injecting LeafAIScreen module...")
        insert_before = "__r(0);"
        if insert_before not in bundle:
            raise RuntimeError("Cannot find __r(0); in bundle")
        bundle = bundle.replace(insert_before, LEAF_AI_MODULE + "\n" + insert_before, 1)
        print(f"  Module injected. Bundle grew by {len(bundle)-original_size:,} chars")

    # ── 2. Wire 'vision' to the navigation switch ─────────────────────────────
    # Exact target string found in the navigation switch:
    TARGET = "case'sensors':return(0,j.jsx)(x.SensorScreen,{onNavigate:function(e){return b(e)}})"
    
    if "case'vision'" in bundle:
        print("  'vision' case already present in nav switch.")
    elif TARGET in bundle:
        REPLACEMENT = (
            TARGET +
            ";case'vision':return(0,j.jsx)(g.require(9999).LeafAIScreen,{onBack:function(){return b('sensors')}})"
        )
        bundle = bundle.replace(TARGET, REPLACEMENT, 1)
        print("  Navigation case 'vision' wired successfully.")
    else:
        # Try alternate — find a nearby pattern
        alt = "case'sensors'"
        idx = bundle.find(alt)
        if idx != -1:
            # Find end of this case (next 'case' or '}')
            end_bracket = bundle.find("}}", idx)
            if end_bracket != -1:
                insert_point = end_bracket + 2
                vision_case = ";case'vision':return(0,j.jsx)(g.require(9999).LeafAIScreen,{onBack:function(){return b('sensors')}})"
                bundle = bundle[:insert_point] + vision_case + bundle[insert_point:]
                print("  Navigation case 'vision' injected via alternate method.")
        else:
            print("  WARNING: Could not find sensors case to inject vision — manual wiring needed")

    # ── 3. Write patched bundle ───────────────────────────────────────────────
    print(f"Writing patched bundle ({len(bundle):,} chars)...")
    with open(BUNDLE_PATH, "w", encoding="utf-8") as f:
        f.write(bundle)

    final_size = os.path.getsize(BUNDLE_PATH)
    print(f"Done. Bundle on disk: {final_size:,} bytes ({final_size/1024/1024:.1f} MB)")


if __name__ == "__main__":
    main()

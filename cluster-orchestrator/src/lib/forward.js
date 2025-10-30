import axios from 'axios';
export async function safeForward({baseUrl,path,body={},token,attempts=2}){
  let lastErr=null;
  for(let i=0;i<=attempts;i++){
    try{
      const res=await axios.post(`${baseUrl}${path}`,body,{headers:{Authorization:token?`Bearer ${token}`:undefined,"Content-Type":"application/json"}});
      return {ok:true,status:res.status,data:res.data};
    }catch(e){lastErr=e;}
  }
  return {ok:false,error:lastErr?.message||"forward_failed"};
}
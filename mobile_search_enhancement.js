
document.addEventListener('DOMContentLoaded',()=>{
 if(!document.querySelector('.mobile-search-btn')){
   const b=document.createElement('button');
   b.className='mobile-search-btn';
   b.innerHTML='🔍 Search';
   b.onclick=()=>{
      const s=document.querySelector('input[type="search"],input[name="q"],input[type="text"]');
      if(s){s.focus(); s.scrollIntoView({behavior:'smooth'});}
   };
   document.body.appendChild(b);
 }
});

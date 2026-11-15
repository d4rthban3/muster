(function(){var m=document.querySelector('details.menu');if(!m)return;
document.addEventListener('click',function(e){if(m.open&&!m.contains(e.target))m.open=false});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&m.open){m.open=false;m.querySelector('summary').focus()}});
m.addEventListener('click',function(e){if(e.target.closest('a'))m.open=false});})();

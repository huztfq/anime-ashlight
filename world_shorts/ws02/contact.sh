rm -rf cs && mkdir cs && ffmpeg -v error -i "$1" -vf "fps=1/1.5,scale=216:384" cs/%02d.png && python3 -c "
from PIL import Image, ImageDraw; import glob
fs=sorted(glob.glob('cs/*.png')); cols=8; rows=(len(fs)+cols-1)//cols
im=Image.new('RGB',(216*cols,400*rows),'black'); d=ImageDraw.Draw(im)
for i,f in enumerate(fs):
  x,y=216*(i%cols),400*(i//cols); im.paste(Image.open(f),(x,y)); d.text((x+4,y+386),f'{i*1.5:.1f}s',fill='white')
im.save('ws02_contact.jpg',quality=88)"

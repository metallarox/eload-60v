import cv2, numpy as np, sys
def silk_bitmap(D=25.0, res=0.04):
    im=cv2.imread('/home/claude/logo/logo.png'); n=int(D/res)
    s=cv2.resize(im,(n,n),interpolation=cv2.INTER_AREA); mx=s.max(axis=2)
    b=(mx>140).astype(np.uint8)*255
    yy,xx=np.mgrid[:n,:n]; r=np.hypot(xx-n/2,yy-n/2)/(n/2)
    b[r>0.905]=0
    k=int(round(0.17/res)); k+=(k%2==0)
    b=cv2.morphologyEx(b,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
    num,lab,st,_=cv2.connectedComponentsWithStats(b); out=np.zeros_like(b)
    for i in range(1,num):
        if st[i,cv2.CC_STAT_AREA]*res*res>0.3: out[lab==i]=255
    out[(r>0.94)&(r<0.985)]=255
    return out
if __name__=='__main__':
    cv2.imwrite('silk_preview.png',255-silk_bitmap())

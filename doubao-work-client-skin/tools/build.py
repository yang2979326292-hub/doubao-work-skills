from pathlib import Path
import os,subprocess,sys
root=Path(__file__).resolve().parent.parent
if os.name!='nt':raise SystemExit('Build on Windows; do not execute this as a web app.')
compiler=Path(os.environ.get('WINDIR',r'C:\Windows'))/'Microsoft.NET'/'Framework64'/'v4.0.30319'/'csc.exe'
if not compiler.is_file():raise SystemExit('Windows .NET Framework C# compiler not found.')
for name in ('client-info.ps1','shortcut-installer.ps1'):
    p=root/'src'/name
    p.write_text(p.read_text(encoding='utf-8-sig'),encoding='utf-8-sig',newline='')
for source,output in [('SkinLauncher.cs','豆包工作-皮肤启动.exe'),('ClientSkin.cs','豆包客户端皮肤-自动启动版.exe')]:
    subprocess.run([str(compiler),'/nologo','/target:winexe','/optimize+','/out:'+str(root/output),'/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll','/reference:System.Web.Extensions.dll',str(root/'src'/source)],check=True)
print('Build completed. Runtime requires runtime/node.exe and its license from the verified release ZIP.')

using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Drawing;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Runtime.InteropServices;

public class ClientSkin : Form {
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer {MaxJsonLength=2000000};
 readonly string root=AppDomain.CurrentDomain.BaseDirectory;
 string data,node,media="",mediaType="";
 CheckBox enabled;TrackBar opacity,dim;Label opacityValue,dimValue,filename,state;
 Button accentButton,surfaceButton;ComboBox fit;PictureBox preview;
 Color accent=ColorTranslator.FromHtml("#3370ff"),surface=ColorTranslator.FromHtml("#181818");
 System.Windows.Forms.Timer timer;Process worker;bool closing=false,activating=false;Button startButton;
 [DllImport("user32.dll")]static extern bool SetForegroundWindow(IntPtr handle);
 public ClientSkin(){
  data=Path.Combine(root,"data");Directory.CreateDirectory(data);node=Path.Combine(root,"runtime","node.exe");
  Text="豆包工作客户端 · 皮肤设置";StartPosition=FormStartPosition.CenterScreen;Size=new Size(640,760);MinimumSize=new Size(600,650);
  Font=new Font("Microsoft YaHei UI",10);BackColor=Color.FromArgb(248,249,251);AutoScaleMode=AutoScaleMode.Dpi;
  var scroll=new Panel{Dock=DockStyle.Fill,AutoScroll=true,Padding=new Padding(22)};Controls.Add(scroll);
  var flow=new FlowLayoutPanel{FlowDirection=FlowDirection.TopDown,WrapContents=false,AutoSize=true,Dock=DockStyle.Top};scroll.Controls.Add(flow);
  var title=new Label{Text="豆包客户端皮肤",Font=new Font(Font.FontFamily,20,FontStyle.Bold),AutoSize=true,Margin=new Padding(0,0,0,8)};flow.Controls.Add(title);
  flow.Controls.Add(TextLabel("这是客户端专用工具，不打开网页版，也不安装 Chrome 扩展。",548));
  enabled=new CheckBox{Text="启用自定义皮肤",Checked=true,AutoSize=true,Margin=new Padding(0,12,0,12)};flow.Controls.Add(enabled);
  flow.Controls.Add(Heading("背景图片 / 视频"));
  var mediaRow=Row();Button image=Button("导入图片"),video=Button("导入视频"),clear=Button("清除背景");mediaRow.Controls.AddRange(new Control[]{image,video,clear});flow.Controls.Add(mediaRow);
  image.Click+=(s,e)=>Import(false);video.Click+=(s,e)=>Import(true);clear.Click+=(s,e)=>{media="";mediaType="";filename.Text="未选择背景";if(preview.Image!=null){preview.Image.Dispose();preview.Image=null;}};
  filename=TextLabel("未选择背景",548);flow.Controls.Add(filename);
  preview=new PictureBox{Size=new Size(548,130),SizeMode=PictureBoxSizeMode.Zoom,BackColor=Color.FromArgb(232,235,240),Margin=new Padding(0,4,0,8)};flow.Controls.Add(preview);
  flow.Controls.Add(TextLabel("文件只保存在本机。视频在客户端内静音循环；此处不冒充视频播放预览。单文件上限 150 MB。",548));
  fit=new ComboBox{DropDownStyle=ComboBoxStyle.DropDownList,Width=240};fit.Items.AddRange(new object[]{"铺满背景（可能裁切）","完整显示（保留边缘）"});fit.SelectedIndex=0;flow.Controls.Add(fit);
  dimValue=TextLabel("背景遮罩 18%",548);flow.Controls.Add(dimValue);dim=Slider(18);flow.Controls.Add(dim);dim.ValueChanged+=(s,e)=>dimValue.Text="背景遮罩 "+dim.Value+"%";
  flow.Controls.Add(Heading("对话区域和主题颜色"));
  var colors=Row();accentButton=Button("主题颜色");surfaceButton=Button("对话底色");colors.Controls.AddRange(new Control[]{accentButton,surfaceButton});flow.Controls.Add(colors);
  accentButton.Click+=(s,e)=>ChooseColor(true);surfaceButton.Click+=(s,e)=>ChooseColor(false);
  opacityValue=TextLabel("统一不透明度 82%",548);flow.Controls.Add(opacityValue);opacity=Slider(82);flow.Controls.Add(opacity);opacity.ValueChanged+=(s,e)=>opacityValue.Text="统一不透明度 "+opacity.Value+"%";
  flow.Controls.Add(TextLabel("0% 完全透明，100% 完全不透明。聊天面板、气泡和输入框使用一个值；文字保持清晰。",548));
  var actions=Row();Button save=Button("保存设置"),reset=Button("恢复默认"),start=Button("启用客户端换肤"),restore=Button("恢复官方外观");startButton=start;save.BackColor=Color.FromArgb(51,112,255);save.ForeColor=Color.White;actions.Controls.AddRange(new Control[]{save,reset,start,restore});flow.Controls.Add(actions);
  save.Click+=(s,e)=>SaveSettings();reset.Click+=(s,e)=>{enabled.Checked=true;accent=ColorTranslator.FromHtml("#3370ff");surface=ColorTranslator.FromHtml("#181818");opacity.Value=82;dim.Value=18;fit.SelectedIndex=0;media="";mediaType="";filename.Text="未选择背景";if(preview.Image!=null){preview.Image.Dispose();preview.Image=null;}SaveSettings();};
  start.Click+=async(s,e)=>await EnableClientSkin();
  restore.Click+=async(s,e)=>{restore.Enabled=false;try{await StopWorker();string result=await RunNode("restore");UpdateState();}catch(Exception ex){state.Text="恢复失败："+ex.Message;}finally{restore.Enabled=true;}};
  state=new Label{Text="正在核对客户端连接……",AutoSize=false,Size=new Size(548,95),ForeColor=Color.FromArgb(54,65,81),Margin=new Padding(0,12,0,0)};flow.Controls.Add(state);
  flow.Controls.Add(TextLabel("关闭设置窗口不会停止皮肤后台。后台随客户端退出；桌面和开始菜单启动器会自动载入已保存皮肤。",548));
  LoadSettings();timer=new System.Windows.Forms.Timer{Interval=1200};timer.Tick+=(s,e)=>{UpdateState();string open=Path.Combine(data,"open-settings.request");if(File.Exists(open)){try{File.Delete(open);}catch{}Show();WindowState=FormWindowState.Normal;SetForegroundWindow(Handle);}};
  Shown+=(s,e)=>{StartWorker();timer.Start();};FormClosing+=(s,e)=>{closing=true;timer.Stop();};
 }
 static Label TextLabel(string text,int width){return new Label{Text=text,Width=width,AutoSize=true,MaximumSize=new Size(width,0),Margin=new Padding(0,4,0,8)};}
 static Label Heading(string text){return new Label{Text=text,AutoSize=true,Font=new Font("Microsoft YaHei UI",12,FontStyle.Bold),Margin=new Padding(0,12,0,6)};}
 static FlowLayoutPanel Row(){return new FlowLayoutPanel{AutoSize=true,FlowDirection=FlowDirection.LeftToRight,WrapContents=true,MaximumSize=new Size(560,0),Margin=new Padding(0,0,0,4)};}
 static Button Button(string text){return new Button{Text=text,AutoSize=true,Height=38,MinimumSize=new Size(104,38),FlatStyle=FlatStyle.Flat,Margin=new Padding(0,4,8,4)};}
 static TrackBar Slider(int value){return new TrackBar{Width=548,Minimum=0,Maximum=100,Value=value,TickFrequency=10,Height=45,Margin=new Padding(0)};}
 void ChooseColor(bool isAccent){using(var picker=new ColorDialog{FullOpen=true,Color=isAccent?accent:surface}){if(picker.ShowDialog(this)==DialogResult.OK){if(isAccent)accent=picker.Color;else surface=picker.Color;UpdateColors();}}}
 void UpdateColors(){accentButton.BackColor=accent;accentButton.ForeColor=accent.GetBrightness()<.55?Color.White:Color.Black;surfaceButton.BackColor=surface;surfaceButton.ForeColor=surface.GetBrightness()<.55?Color.White:Color.Black;}
 void Import(bool video){using(var picker=new OpenFileDialog{Title=video?"选择本地背景视频":"选择本地背景图片",Filter=video?"MP4 / WebM 视频|*.mp4;*.webm":"图片|*.png;*.jpg;*.jpeg;*.webp;*.gif",Multiselect=false}){if(picker.ShowDialog(this)!=DialogResult.OK)return;
  try{var file=new FileInfo(picker.FileName);if(file.Length<=0||file.Length>150L*1024*1024)throw new Exception("文件为空或超过150MB");
   var ext=file.Extension.ToLowerInvariant();string type=Mime(ext);if(type.Length==0||video!=type.StartsWith("video/"))throw new Exception("文件类型不支持");
   byte[] header=new byte[32];using(var stream=File.OpenRead(file.FullName))stream.Read(header,0,header.Length);if(!ValidHeader(ext,header))throw new Exception("文件头与扩展名不匹配");
   Image bitmap=null;if(!video&&ext!=".webp"){using(var source=Image.FromFile(file.FullName))bitmap=new Bitmap(source);}
   string folder=Path.Combine(data,"media");Directory.CreateDirectory(folder);string name=Guid.NewGuid().ToString()+ext;File.Copy(file.FullName,Path.Combine(folder,name),false);media=name;mediaType=type;filename.Text=file.Name+" · "+(file.Length/1024d/1024d).ToString("0.0")+" MB";
   if(preview.Image!=null)preview.Image.Dispose();preview.Image=bitmap;state.Text=video?"视频已导入本机，点击保存。实际编码解码和播放会在客户端内验证。":"图片已导入本机，点击保存并应用。";
  }catch(Exception ex){state.Text="导入失败，原背景未替换："+ex.Message;}
 }}
 public static string Mime(string ext){switch(ext){case ".png":return "image/png";case ".jpg":case ".jpeg":return "image/jpeg";case ".webp":return "image/webp";case ".gif":return "image/gif";case ".mp4":return "video/mp4";case ".webm":return "video/webm";default:return "";}}
 public static bool ValidHeader(string ext,byte[] b){if(b.Length<16)return false;switch(ext){case ".png":return b[0]==137&&b[1]==80&&b[2]==78&&b[3]==71;case ".jpg":case ".jpeg":return b[0]==255&&b[1]==216&&b[2]==255;case ".gif":return Encoding.ASCII.GetString(b,0,6)=="GIF87a"||Encoding.ASCII.GetString(b,0,6)=="GIF89a";case ".webp":return Encoding.ASCII.GetString(b,0,4)=="RIFF"&&Encoding.ASCII.GetString(b,8,4)=="WEBP";case ".mp4":return Encoding.ASCII.GetString(b,4,4)=="ftyp";case ".webm":return b[0]==26&&b[1]==69&&b[2]==223&&b[3]==163;default:return false;}}
 Dictionary<string,object> Settings(){return new Dictionary<string,object>{{"version",1},{"enabled",enabled.Checked},{"accent","#"+accent.R.ToString("x2")+accent.G.ToString("x2")+accent.B.ToString("x2")},{"surface","#"+surface.R.ToString("x2")+surface.G.ToString("x2")+surface.B.ToString("x2")},{"opacity",opacity.Value/100d},{"dim",dim.Value/100d},{"fit",fit.SelectedIndex==1?"contain":"cover"},{"media",media},{"mediaType",mediaType}};}
 bool SaveSettings(){try{var path=Path.Combine(data,"settings.json");var temp=path+".tmp";File.WriteAllText(temp,Json.Serialize(Settings()),new UTF8Encoding(false));if(File.Exists(path))File.Replace(temp,path,null);else File.Move(temp,path);StartWorker();state.Text="设置已保存。只有主窗口接口可用时才会应用；首次使用请点击“启用客户端换肤”。";return true;}catch(Exception ex){state.Text="保存失败："+ex.Message;return false;}}
 void LoadSettings(){try{var p=Path.Combine(data,"settings.json");if(!File.Exists(p)){UpdateColors();return;}var c=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(p,Encoding.UTF8));enabled.Checked=Convert.ToBoolean(c["enabled"]);accent=ColorTranslator.FromHtml(Convert.ToString(c["accent"]));surface=ColorTranslator.FromHtml(Convert.ToString(c["surface"]));opacity.Value=Math.Max(0,Math.Min(100,(int)Math.Round(Convert.ToDouble(c["opacity"])*100)));dim.Value=Math.Max(0,Math.Min(100,(int)Math.Round(Convert.ToDouble(c["dim"])*100)));fit.SelectedIndex=Convert.ToString(c["fit"])=="contain"?1:0;media=Convert.ToString(c["media"]);mediaType=Convert.ToString(c["mediaType"]);filename.Text=media.Length>0?"已有本地背景 · "+mediaType:"未选择背景";UpdateColors();}catch(Exception ex){state.Text="设置读取失败，未覆盖原文件："+ex.Message;}}
 bool ClientStillRunning(string executable){
  foreach(var process in Process.GetProcessesByName("DoubaoWork"))using(process){try{if(string.Equals(process.MainModule.FileName,executable,StringComparison.OrdinalIgnoreCase))return true;}catch(System.ComponentModel.Win32Exception){throw new Exception("无法核对仍运行的客户端进程，未自动启动新实例。请正常退出豆包工作后重试。");}catch(InvalidOperationException){}}
  return false;
 }
 public static string DebugArguments(int port){if(port<1024||port>65535)throw new ArgumentOutOfRangeException("port");return "--remote-debugging-address=127.0.0.1 --remote-debugging-port="+port.ToString(System.Globalization.CultureInfo.InvariantCulture);}
 int FreeDebugPort(){for(int p=9342;p<9348;p++){var listener=new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback,p);try{listener.Start();return p;}catch(System.Net.Sockets.SocketException){}finally{listener.Stop();}}throw new Exception("本机换肤调试端口被占用，未改变其他程序。");}
 async System.Threading.Tasks.Task EnableClientSkin(){
  if(activating)return;activating=true;startButton.Enabled=false;
  try{
   if(!SaveSettings())return;string inspection=await RunNode("inspect");var statusFile=Path.Combine(data,"status.json");var current=Json.Deserialize<Dictionary<string,object>>(inspection);
   if(Convert.ToBoolean(current["ready"])){StartWorker();state.Text="主窗口接口已可用，正在应用已保存设置。";return;}
   var info=await RunInfo();var executable=Convert.ToString(info["executable"]);
   var deadline=DateTime.UtcNow.AddMinutes(5);
   while(ClientStillRunning(executable)){
    if(closing||IsDisposed)return;
    state.Text="设置已保存，尚未生效。请等当前任务结束后，从豆包工作原生菜单或托盘正常退出。\r\n保持本设置窗口打开；检测到完全退出后，会自动带换肤参数启动客户端。\r\n不会强制结束任务；5 分钟后停止等待。";
    if(DateTime.UtcNow>=deadline)throw new Exception("等待客户端退出超时；设置已保留。正常退出豆包工作后再次点击“启用客户端换肤”。");
    await System.Threading.Tasks.Task.Delay(1000);
   }
   if(closing||IsDisposed)return;
   int port=FreeDebugPort();state.Text="正在带换肤参数启动豆包工作，并核验主窗口接口……";
   using(var process=Process.Start(new ProcessStartInfo(executable,DebugArguments(port)){UseShellExecute=false,WorkingDirectory=Path.GetDirectoryName(executable)})){}
   StartWorker();var verifyDeadline=DateTime.UtcNow.AddSeconds(60);
   while(DateTime.UtcNow<verifyDeadline){
    if(closing||IsDisposed)return;await System.Threading.Tasks.Task.Delay(1800);
    if(!File.Exists(statusFile))continue;
    var result=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(statusFile,Encoding.UTF8));string phase=Convert.ToString(result["phase"]);
    DateTime stamp;if(!DateTime.TryParse(Convert.ToString(result["updatedAt"]),out stamp)||DateTime.UtcNow-stamp.ToUniversalTime()>TimeSpan.FromSeconds(15))continue;
    if(phase=="applied"||phase=="disabled"){state.Text=Convert.ToString(result["message"]);return;}
    if(phase=="error"||phase=="not-applied")state.Text="客户端已启动，尚未通过换肤核验："+Convert.ToString(result["message"]);
   }
   state.Text="客户端已请求带参数启动，但主窗口换肤核验未通过。请将当前提示发给我；不要继续反复保存或恢复默认。";
  }catch(Exception ex){state.Text="启用未完成："+ex.Message;}finally{activating=false;if(!IsDisposed)startButton.Enabled=true;}
 }
 void StartWorker(){try{if(worker!=null&&!worker.HasExited)return;if(!File.Exists(node))throw new Exception("包内 Node 运行时缺失");var stop=Path.Combine(data,"stop.request");if(File.Exists(stop))File.Delete(stop);worker=Process.Start(new ProcessStartInfo(node,"\""+Path.Combine(root,"src","host-fixed.mjs")+"\" watch --exit-with-client"){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=root});}catch(Exception ex){state.Text="皮肤宿主未启动："+ex.Message;}}
 async System.Threading.Tasks.Task StopWorker(){var lockFile=Path.Combine(data,"worker.lock");if(File.Exists(lockFile)){File.WriteAllText(Path.Combine(data,"stop.request"),"stop",new UTF8Encoding(false));for(int i=0;i<650&&File.Exists(lockFile);i++)await System.Threading.Tasks.Task.Delay(100);if(File.Exists(lockFile))throw new Exception("皮肤宿主尚未停止，未强制结束任何进程");}worker=null;}
 async System.Threading.Tasks.Task<string> RunNode(string mode){return await System.Threading.Tasks.Task.Run(()=>{using(var p=new Process{StartInfo=new ProcessStartInfo(node,"\""+Path.Combine(root,"src","host-fixed.mjs")+"\" "+mode){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=root,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8}}){p.Start();string result=p.StandardOutput.ReadToEnd(),error=p.StandardError.ReadToEnd();p.WaitForExit();if(p.ExitCode!=0)throw new Exception(error);return result;}});}
 async System.Threading.Tasks.Task<Dictionary<string,object>> RunInfo(){return await System.Threading.Tasks.Task.Run(()=>{var p=new Process{StartInfo=new ProcessStartInfo("powershell.exe","-NoProfile -ExecutionPolicy Bypass -File \""+Path.Combine(root,"src","client-info.ps1")+"\" -Action Inspect"){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8}};p.Start();var text=p.StandardOutput.ReadToEnd();var err=p.StandardError.ReadToEnd();p.WaitForExit();if(p.ExitCode!=0)throw new Exception(err);p.Dispose();return Json.Deserialize<Dictionary<string,object>>(text.Trim().TrimStart('\uFEFF'));});}
 void UpdateState(){if(activating)return;try{var p=Path.Combine(data,"status.json");if(!File.Exists(p))return;var c=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(p,Encoding.UTF8));state.Text=Convert.ToString(c["message"])+"\r\n核验时间："+Convert.ToString(c["updatedAt"]);var elapsed=DateTime.UtcNow-DateTime.Parse(Convert.ToString(c["updatedAt"])).ToUniversalTime();if(elapsed.TotalSeconds>20)state.Text="连接状态已过期，不能据此判断当前皮肤生效。\r\n"+state.Text;}catch{}}
 [STAThread]public static int Main(string[] args){if(args.Contains("--self-test")){bool ok=DebugArguments(9342)=="--remote-debugging-address=127.0.0.1 --remote-debugging-port=9342"&&Mime(".mp4")=="video/mp4"&&Mime(".exe")==""&&ValidHeader(".png",new byte[]{137,80,78,71,13,10,26,10,0,0,0,0,0,0,0,0});File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"tests","native-test.json"),"{\"passed\":"+(ok?"true":"false")+"}",Encoding.UTF8);return ok?0:1;}
  bool created;using(var mutex=new System.Threading.Mutex(true,"Local\\DoubaoClientSkin_"+BitConverter.ToString(SHA256.Create().ComputeHash(Encoding.UTF8.GetBytes(AppDomain.CurrentDomain.BaseDirectory))).Replace("-",""),out created)){if(!created){File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"data","open-settings.request"),"open",new UTF8Encoding(false));return 0;}Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new ClientSkin());return 0;}}
}

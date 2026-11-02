using System;
using System.IO;
using System.Diagnostics;
using System.Drawing;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

// External launcher: never modifies the official executable/profile/registry.
public sealed class SkinLauncher : Form {
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
 static readonly string Root=AppDomain.CurrentDomain.BaseDirectory;
 Label message; bool cancel=false;
 public SkinLauncher(){
  Text="豆包工作 · 皮肤启动";Size=new Size(530,220);StartPosition=FormStartPosition.CenterScreen;
  Font=new Font("Microsoft YaHei UI",10);BackColor=Color.FromArgb(248,249,251);
  message=new Label{Dock=DockStyle.Fill,Padding=new Padding(24),Text="正在检查客户端与已保存皮肤……"};Controls.Add(message);
  var stop=new Button{Text="取消此次启动",Dock=DockStyle.Bottom,Height=40};Controls.Add(stop);stop.Click+=(s,e)=>{cancel=true;Close();};
  Shown+=async(s,e)=>await Launch();FormClosing+=(s,e)=>cancel=true;
 }
 static async Task<System.Collections.Generic.Dictionary<string,object>> Info(){
  return await Task.Run(()=>{using(var p=new Process{StartInfo=new ProcessStartInfo("powershell.exe","-NoProfile -ExecutionPolicy Bypass -File \""+Path.Combine(Root,"src","client-info.ps1")+"\" -Action Inspect"){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8}}){p.Start();string output=p.StandardOutput.ReadToEnd(),error=p.StandardError.ReadToEnd();if(!p.WaitForExit(65000))throw new Exception("客户端检查超时；未结束任何程序。");if(p.ExitCode!=0)throw new Exception(error);return Json.Deserialize<System.Collections.Generic.Dictionary<string,object>>(output.Trim().TrimStart('\uFEFF'));}});
 }
 public static string DebugArguments(int port){if(port<1024||port>65535)throw new ArgumentOutOfRangeException("port");return "--remote-debugging-address=127.0.0.1 --remote-debugging-port="+port;}
 static int FreePort(){for(int port=9342;port<=9347;port++){var listener=new TcpListener(IPAddress.Loopback,port);try{listener.Start();return port;}catch(SocketException){}finally{listener.Stop();}}throw new Exception("换肤端口被占用；未影响其他应用。");}
 static async Task StopPreviousHost(){
  string file=Path.Combine(Root,"data","worker.lock");if(!File.Exists(file))return;
  var record=Json.Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(file,Encoding.UTF8));int pid=Convert.ToInt32(record["pid"]);
  try{using(var p=Process.GetProcessById(pid)){if(p.HasExited)return;}}catch(ArgumentException){return;}
  File.WriteAllText(Path.Combine(Root,"data","stop.request"),"stop",new UTF8Encoding(false));
  DateTime limit=DateTime.UtcNow.AddSeconds(65);while(File.Exists(file)&&DateTime.UtcNow<limit)await Task.Delay(200);
  if(File.Exists(file))throw new Exception("上次皮肤后台仍在退出，未重复启动。请稍后再从入口打开。");
 }
 static void StartHost(int port){
  string node=Path.Combine(Root,"runtime","node.exe"),script=Path.Combine(Root,"src","host-fixed.mjs");
  if(!File.Exists(node)||!File.Exists(script))throw new Exception("启动包不完整；请保留 src 和 runtime 文件夹。");
  string stop=Path.Combine(Root,"data","stop.request");if(File.Exists(stop))File.Delete(stop);
  using(var p=Process.Start(new ProcessStartInfo(node,"\""+script+"\" watch --exit-with-client --port "+port){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=Root})){}
 }
 async Task Launch(){try{
  // Existing configuration is required: never silently replace a user's skin by defaults.
  string settings=Path.Combine(Root,"data","settings.json");if(!File.Exists(settings))throw new Exception("尚未保存皮肤。请先打开本目录的皮肤设置程序保存背景和颜色。");
  Json.DeserializeObject(File.ReadAllText(settings,Encoding.UTF8));
  var info=await Info();string exe=Convert.ToString(info["executable"]);
  if(!File.Exists(exe)||!string.Equals(Path.GetFileName(exe),"DoubaoWork.exe",StringComparison.OrdinalIgnoreCase))throw new Exception("未找到真实豆包工作客户端。");
  // Reuse an already-enabled instance. Do not send a second launch to Chromium.
  int runningPort=info.ContainsKey("mainDebugPort")?Convert.ToInt32(info["mainDebugPort"]):0;
  if(Convert.ToBoolean(info["running"])&&runningPort>=9342&&runningPort<=9347){StartHost(runningPort);using(var p=Process.Start(new ProcessStartInfo(exe,DebugArguments(runningPort)){UseShellExecute=false,WorkingDirectory=Path.GetDirectoryName(exe)})){}Close();return;}
  DateTime deadline=DateTime.UtcNow.AddMinutes(5);
  while(Convert.ToBoolean(info["running"])){
   message.Text="当前豆包工作是普通启动，暂时无法自动恢复皮肤。\r\n\r\n请等任务结束后，通过豆包工作菜单或托盘正常退出。此窗口会等待并自动重新打开，最长 5 分钟；不会强制结束任务。";
   if(cancel)return;if(DateTime.UtcNow>=deadline)throw new Exception("等待退出超时，皮肤仍已保存。下次正常退出后，从桌面或开始菜单打开即可。");
   await Task.Delay(2500);if(cancel)return;info=await Info();
  }
  if(cancel)return;await StopPreviousHost();if(cancel)return;int port=FreePort();
  message.Text="正在启动豆包工作并自动恢复皮肤……";
  using(var p=Process.Start(new ProcessStartInfo(exe,DebugArguments(port)){UseShellExecute=false,WorkingDirectory=Path.GetDirectoryName(exe)})){}
  StartHost(port);
  // The host verifies the live renderer and writes status.json; process creation alone is not success.
  DateTime verify=DateTime.UtcNow.AddSeconds(90);string status=Path.Combine(Root,"data","status.json");DateTime begin=DateTime.UtcNow;
  while(DateTime.UtcNow<verify&&!cancel){await Task.Delay(1000);try{if(!File.Exists(status))continue;var s=Json.Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(status,Encoding.UTF8));DateTime stamp;if(!DateTime.TryParse(Convert.ToString(s["updatedAt"]),out stamp)||stamp.ToUniversalTime()<begin)continue;string phase=Convert.ToString(s["phase"]);message.Text=Convert.ToString(s["message"]);if(phase=="applied"||phase=="disabled"){Close();return;}}catch(IOException){}catch(ArgumentException){}}
  if(!cancel)throw new Exception("客户端已请求启动，但皮肤尚未通过核验。请查看本目录 data/status.json；不会重复重启或改动已保存皮肤。");
 }catch(Exception ex){if(!cancel)message.Text="启动未完成："+ex.Message;}}
 [STAThread]public static int Main(string[] args){
  if(Array.IndexOf(args,"--install-shortcuts")>=0||Array.IndexOf(args,"--restore-shortcuts")>=0){string action=Array.IndexOf(args,"--restore-shortcuts")>=0?"Restore":"Install";using(var p=Process.Start(new ProcessStartInfo("powershell.exe","-NoProfile -ExecutionPolicy Bypass -File \""+Path.Combine(Root,"src","shortcut-installer.ps1")+"\" -Action "+action){UseShellExecute=false,CreateNoWindow=true})){p.WaitForExit();return p.ExitCode;}}
  if(Array.IndexOf(args,"--self-test")>=0){bool passed=DebugArguments(9342)=="--remote-debugging-address=127.0.0.1 --remote-debugging-port=9342";Console.WriteLine(passed?"passed":"failed");return passed?0:1;}
  bool created;using(var mutex=new System.Threading.Mutex(true,"Local\\DoubaoWorkSkinLauncher",out created)){if(!created)return 0;Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new SkinLauncher());return 0;}
 }
}

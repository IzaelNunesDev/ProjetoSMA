
import React, { useState } from "react";
import { CardSection } from "@/components/ui/CardSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Folder, Bell, Shield, Cpu, HardDrive, Trash2, Plus } from "lucide-react";

export default function Settings() {
  const [autoOrganize, setAutoOrganize] = useState(true);
  const [notifications, setNotifications] = useState(true);
  const [deepScan, setDeepScan] = useState(false);
  const [watchedPaths, setWatchedPaths] = useState([
    "/Users/john/Downloads",
    "/Users/john/Documents",
    "/Users/john/Desktop"
  ]);
  const [newPath, setNewPath] = useState("");

  const addWatchedPath = () => {
    if (newPath.trim() && !watchedPaths.includes(newPath.trim())) {
      setWatchedPaths([...watchedPaths, newPath.trim()]);
      setNewPath("");
    }
  };

  const removeWatchedPath = (path: string) => {
    setWatchedPaths(watchedPaths.filter(p => p !== path));
  };

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
        <p className="text-slate-400">Configure your File Agent Control Center</p>
      </div>

      {/* General Settings */}
      <CardSection>
        <div className="flex items-center gap-3 mb-6">
          <Cpu className="w-6 h-6 text-blue-400" />
          <h2 className="text-xl font-bold text-white">General Settings</h2>
        </div>
        
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-white">Auto-organize files</h3>
              <p className="text-sm text-slate-400">Automatically organize files when suggestions are approved</p>
            </div>
            <Switch
              checked={autoOrganize}
              onCheckedChange={setAutoOrganize}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-white">Enable notifications</h3>
              <p className="text-sm text-slate-400">Show system notifications for agent activities</p>
            </div>
            <Switch
              checked={notifications}
              onCheckedChange={setNotifications}
            />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-white">Deep content scanning</h3>
              <p className="text-sm text-slate-400">Analyze file contents for better organization (slower)</p>
            </div>
            <Switch
              checked={deepScan}
              onCheckedChange={setDeepScan}
            />
          </div>

          <div>
            <h3 className="font-semibold text-white mb-2">Scan frequency</h3>
            <Select defaultValue="medium">
              <SelectTrigger className="bg-slate-700 border-slate-600 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low (every 30 minutes)</SelectItem>
                <SelectItem value="medium">Medium (every 10 minutes)</SelectItem>
                <SelectItem value="high">High (every 5 minutes)</SelectItem>
                <SelectItem value="realtime">Real-time (immediate)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardSection>

      {/* Watched Directories */}
      <CardSection>
        <div className="flex items-center gap-3 mb-6">
          <Folder className="w-6 h-6 text-green-400" />
          <h2 className="text-xl font-bold text-white">Watched Directories</h2>
        </div>

        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              value={newPath}
              onChange={(e) => setNewPath(e.target.value)}
              placeholder="Enter directory path to monitor..."
              className="flex-1 bg-slate-700 border-slate-600"
              onKeyPress={(e) => e.key === 'Enter' && addWatchedPath()}
            />
            <Button onClick={addWatchedPath} className="bg-green-600 hover:bg-green-700">
              <Plus className="w-4 h-4" />
            </Button>
          </div>

          <div className="space-y-2">
            {watchedPaths.map((path, index) => (
              <div key={index} className="flex items-center justify-between bg-slate-700/50 border border-slate-600 rounded-lg p-3">
                <div className="flex items-center gap-3">
                  <Folder className="w-4 h-4 text-blue-400" />
                  <span className="text-slate-200">{path}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeWatchedPath(path)}
                  className="text-slate-400 hover:text-red-400"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      </CardSection>

      {/* System Information */}
      <CardSection>
        <div className="flex items-center gap-3 mb-6">
          <HardDrive className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-bold text-white">System Information</h2>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold text-white mb-2">Memory Usage</h3>
            <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-slate-300">Indexed Files</span>
                <span className="text-white font-semibold">2,847</span>
              </div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-slate-300">Memory Entries</span>
                <span className="text-white font-semibold">15,923</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-300">Storage Used</span>
                <span className="text-white font-semibold">156 MB</span>
              </div>
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-white mb-2">Agent Status</h3>
            <div className="bg-slate-700/50 border border-slate-600 rounded-lg p-4">
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Scanner Agent</span>
                  <span className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Organize Agent</span>
                  <span className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Suggest Agent</span>
                  <span className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <Button variant="outline" className="bg-slate-700 border-slate-600">
            Clear Cache
          </Button>
          <Button variant="outline" className="bg-slate-700 border-slate-600">
            Export Settings
          </Button>
          <Button variant="outline" className="bg-slate-700 border-slate-600">
            Reset to Defaults
          </Button>
        </div>
      </CardSection>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { getCameras, createCamera, type Camera } from '../api/cameras';
import { Camera as CameraIcon, Plus, Save } from 'lucide-react';

export default function Cameras() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  
  const [newCamera, setNewCamera] = useState<Partial<Camera>>({
    name: '',
    location: '',
    source: '',
    timezone: 'UTC'
  });

  const loadCameras = () => {
    setLoading(true);
    getCameras()
      .then(setCameras)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    // eslint-disable-next-line react/set-state-in-effect
    loadCameras();
  }, []);



  const handleCreate = async () => {
    try {
      await createCamera(newCamera);
      setShowForm(false);
      setNewCamera({ name: '', location: '', source: '', timezone: 'UTC' });
      loadCameras();
    } catch (err: any) {
      alert(`Failed to create camera: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold flex items-center">
          <CameraIcon className="w-6 h-6 mr-3 text-indigo-400" />
          Camera Management
        </h1>
        <button 
          onClick={() => setShowForm(!showForm)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center transition-colors"
        >
          <Plus className="w-4 h-4 mr-2" /> Add Camera
        </button>
      </div>

      {showForm && (
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg">
          <h2 className="text-lg font-medium mb-4">New Camera</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Name</label>
              <input 
                type="text" 
                value={newCamera.name}
                onChange={e => setNewCamera({...newCamera, name: e.target.value})}
                className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-indigo-500" 
                placeholder="e.g. CAM-01 Main Gate"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Location</label>
              <input 
                type="text" 
                value={newCamera.location}
                onChange={e => setNewCamera({...newCamera, location: e.target.value})}
                className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-indigo-500" 
                placeholder="e.g. North Entrance"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Source IP/URL</label>
              <input 
                type="text" 
                value={newCamera.source}
                onChange={e => setNewCamera({...newCamera, source: e.target.value})}
                className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-indigo-500" 
                placeholder="e.g. 192.168.1.100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Timezone</label>
              <input 
                type="text" 
                value={newCamera.timezone}
                onChange={e => setNewCamera({...newCamera, timezone: e.target.value})}
                className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-indigo-500" 
              />
            </div>
          </div>
          <div className="flex justify-end space-x-3">
            <button 
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white"
            >
              Cancel
            </button>
            <button 
              onClick={handleCreate}
              disabled={!newCamera.name}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center transition-colors"
            >
              <Save className="w-4 h-4 mr-2" /> Save Camera
            </button>
          </div>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading cameras...</div>
        ) : cameras.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No cameras registered.</div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-950 border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
                <th className="px-6 py-4 font-medium">Name</th>
                <th className="px-6 py-4 font-medium">Location</th>
                <th className="px-6 py-4 font-medium">Source</th>
                <th className="px-6 py-4 font-medium">Timezone</th>
                <th className="px-6 py-4 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {cameras.map(cam => (
                <tr key={cam.id} className="hover:bg-slate-800/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-slate-200">{cam.name}</div>
                    <div className="text-xs text-slate-500 font-mono mt-1">{cam.id}</div>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-300">{cam.location || '-'}</td>
                  <td className="px-6 py-4 text-sm text-slate-300 font-mono">{cam.source || '-'}</td>
                  <td className="px-6 py-4 text-sm text-slate-300">{cam.timezone}</td>
                  <td className="px-6 py-4 text-sm text-slate-400">{new Date(cam.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

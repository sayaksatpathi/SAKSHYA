import { useEffect, useState } from 'react';
import { getCases, createCase, type Case } from '../api/cases';
import { Briefcase, Plus, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';

export default function Cases() {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  
  // Create Case Form
  const [showForm, setShowForm] = useState(false);
  const [newCase, setNewCase] = useState({ title: '', case_number: '', investigator: '' });

  const loadCases = () => {
    setLoading(true);
    getCases()
      .then(setCases)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    // eslint-disable-next-line react/set-state-in-effect
    loadCases();
  }, []);



  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createCase(newCase);
      setShowForm(false);
      setNewCase({ title: '', case_number: '', investigator: '' });
      loadCases();
    } catch (err: any) {
      alert(`Failed to create case: ${err.message}`);
    }
  };

  const filteredCases = cases.filter(c => 
    c.title.toLowerCase().includes(search.toLowerCase()) || 
    c.case_number.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center">
          <Briefcase className="w-6 h-6 mr-3 text-indigo-400" />
          Cases
        </h1>
        <button 
          onClick={() => setShowForm(!showForm)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-md font-medium flex items-center transition-colors"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Case
        </button>
      </div>

      {showForm && (
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg">
          <h2 className="text-lg font-medium mb-4">Create New Case</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Case Number</label>
                <input 
                  required
                  type="text" 
                  className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  value={newCase.case_number}
                  onChange={e => setNewCase({...newCase, case_number: e.target.value})}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Investigator</label>
                <input 
                  required
                  type="text" 
                  className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  value={newCase.investigator}
                  onChange={e => setNewCase({...newCase, investigator: e.target.value})}
                />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-slate-400 mb-1">Title</label>
                <input 
                  required
                  type="text" 
                  className="w-full bg-slate-950 border border-slate-700 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  value={newCase.title}
                  onChange={e => setNewCase({...newCase, title: e.target.value})}
                />
              </div>
            </div>
            <div className="flex justify-end space-x-3">
              <button 
                type="button" 
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-slate-400 hover:text-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button 
                type="submit"
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-md font-medium transition-colors"
              >
                Create
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col">
        <div className="p-4 border-b border-slate-800 flex items-center bg-slate-900/50">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search cases..." 
              className="w-full bg-slate-950 border border-slate-700 rounded-md pl-9 pr-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400">Loading cases...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-400">Error: {error}</div>
        ) : filteredCases.length === 0 ? (
          <div className="p-8 text-center text-slate-400">No cases found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-medium">
                <tr>
                  <th className="px-6 py-3">Case ID</th>
                  <th className="px-6 py-3">Title</th>
                  <th className="px-6 py-3">Investigator</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Created</th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredCases.map(c => (
                  <tr key={c.id} className="hover:bg-slate-800/50 transition-colors">
                    <td className="px-6 py-4 font-mono text-indigo-400">{c.case_number}</td>
                    <td className="px-6 py-4 font-medium">{c.title}</td>
                    <td className="px-6 py-4">{c.investigator}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                        c.status === 'OPEN' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400">
                      {format(new Date(c.created_at), 'MMM d, yyyy HH:mm')}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link to={`/cases/${c.id}`} className="text-indigo-400 hover:text-indigo-300 font-medium">
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

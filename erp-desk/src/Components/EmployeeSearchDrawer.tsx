import { useState } from "react";
import { FaCaretLeft } from "react-icons/fa";

const EmployeeSearchDrawer = () => {
  const [showDrawer, setShowDrawer] = useState(false);

  return (
    <>
      {/* Drawer Toggle Button */}
      <div
        className="fixed top-1/2 right-0 -translate-y-1/2 bg-[#E6FEE7] text-white rounded-l cursor-pointer py-10 z-9999999 px-1"
        onClick={() => setShowDrawer(!showDrawer)}
      >
        <FaCaretLeft className={`text-[#4D8C52] transition-transform duration-300 ${showDrawer ? "-rotate-180" : ""
          }`}
        />
      </div>

      {/* Side Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-64 bg-white shadow-lg border-l transition-transform duration-300 z-40 ${showDrawer ? "translate-x-0" : "translate-x-full"
          }`}
      >
        <div className="p-4 border-b">
          <input
            type="text"
            placeholder="Search employees..."
            className="w-full px-3 py-2 border rounded outline-none focus:ring focus:ring-blue-200"
          />
        </div>

        <div className="p-4 flex flex-col items-center justify-center h-full">
          <div className="animate-spin border-4 border-gray-300 border-t-blue-500 rounded-full w-10 h-10 mb-2"></div>
          <p className="text-gray-500">Click to load employees...</p>
        </div>
      </div>
    </>
  );
};

export default EmployeeSearchDrawer;

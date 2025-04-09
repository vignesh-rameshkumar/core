import React from 'react';

type WorkingHoursData = {
  [key: string]: number;
};

interface WorkingHoursBarGraphProps {
  data: WorkingHoursData;
  maxHours?: number;
}


const WorkingHoursBarGraph: React.FC<WorkingHoursBarGraphProps> = ({
  data,
  maxHours,
}) => {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const calculatedMax =
    maxHours || Math.max(...Object.values(data), 8); // fallback to 8

  return (
    <div className='flex gap-3 py-4 px-2 bg-[#FFFFFF99] rounded-xl justify-center'>
      {days.map((day) => {
        const hours = data[day] || 0;
        const heightPercent = (hours / calculatedMax) * 100;

        return (
          <div key={day} className='flex flex-col items-center w-[40px]'>
            <div className='h-[80px] w-full flex items-end justify-center bg-[#ffffff30] rounded-md overflow-hidden'>
              {hours > 0 && (
                <div
                  className='bg-[#3F7343] w-[80%] rounded transition-all duration-300'
                  style={{ height: `${heightPercent}%` }}
                  title={`${hours} hrs`}
                />
              )}
            </div>
            <p className='!uppercase text-xs mt-1 text-[#181D27]'>{day}</p>
          </div>
        );
      })}
    </div>
  );
};

export default WorkingHoursBarGraph;

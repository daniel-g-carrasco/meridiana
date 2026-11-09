// A Revit add-in that exports one model to IFC and closes Revit: the local way from a .rvt to a model Meridiana reads
// (study 32). It does nothing unless the environment names a job, so it never disturbs a Revit opened by hand.
//
//   MERIDIANA_RVT_JOB = a text file of lines key=value:
//       source=<a LOCAL COPY of the .rvt: never the server's file>
//       folder=<where the IFC goes>
//       name=<the IFC's name, without .ifc>
//       version=IFC2x3CV2 | IFC4RV | IFC4DTV
//   The answer is written to <folder>\<name>.esito.txt: "ok" or "error: ...".
//
// The file is opened detached from its central model, its worksets closed; nothing is saved: an upgrade from an older
// version stays in memory. Built against Revit 2023's API (.NET Framework 4.8), see tools/revit_export/LEGGIMI.md.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

namespace MeridianaIfcExport
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public class App : IExternalApplication
    {
        Dictionary<string, string> job;
        bool started;

        public Result OnStartup(UIControlledApplication app)
        {
            string path = Environment.GetEnvironmentVariable("MERIDIANA_RVT_JOB");
            if (string.IsNullOrEmpty(path) || !File.Exists(path))
                return Result.Succeeded;
            job = File.ReadAllLines(path).Where(l => l.Contains("="))
                      .ToDictionary(l => l.Substring(0, l.IndexOf('=')).Trim(), l => l.Substring(l.IndexOf('=') + 1).Trim());
            app.DialogBoxShowing += Dismiss;
            app.ControlledApplication.FailuresProcessing += Failures;
            app.Idling += Run;
            return Result.Succeeded;
        }

        public Result OnShutdown(UIControlledApplication app) { return Result.Succeeded; }

        // whatever asks a question while nobody is there answers its default: a missing link, a font, an upgrade
        static void Dismiss(object sender, DialogBoxShowingEventArgs e) { e.OverrideResult((int)TaskDialogResult.Close); }

        static void Failures(object sender, FailuresProcessingEventArgs e)
        {
            FailuresAccessor a = e.GetFailuresAccessor();
            foreach (FailureMessageAccessor m in a.GetFailureMessages())
                if (m.GetSeverity() == FailureSeverity.Warning)
                    a.DeleteWarning(m);
            e.SetProcessingResult(FailureProcessingResult.Continue);
        }

        void Run(object sender, IdlingEventArgs e)
        {
            if (started) return;
            started = true;
            UIApplication ui = (UIApplication)sender;
            string answer;
            try
            {
                answer = Export(ui.Application);
            }
            catch (Exception x)
            {
                answer = "error: " + x.GetType().Name + ": " + x.Message;
            }
            File.WriteAllText(Path.Combine(job["folder"], job["name"] + ".esito.txt"), answer);
            ui.PostCommand(RevitCommandId.LookupPostableCommandId(PostableCommand.ExitRevit));
        }

        string Export(Application app)
        {
            ModelPath model = ModelPathUtils.ConvertUserVisiblePathToModelPath(job["source"]);
            OpenOptions open = new OpenOptions();
            BasicFileInfo info = BasicFileInfo.Extract(job["source"]);
            if (info.IsWorkshared)
            {
                open.DetachFromCentralOption = DetachFromCentralOption.DetachAndDiscardWorksets;
                open.SetOpenWorksetsConfiguration(new WorksetConfiguration(WorksetConfigurationOption.OpenAllWorksets));
            }
            Document doc = app.OpenDocumentFile(model, open);
            try
            {
                IFCExportOptions options = new IFCExportOptions();
                IFCVersion version;
                options.FileVersion = Enum.TryParse(job.ContainsKey("version") ? job["version"] : "", out version)
                    ? version : IFCVersion.IFC2x3CV2;
                options.ExportBaseQuantities = false;
                options.WallAndColumnSplitting = false;
                options.SpaceBoundaryLevel = 0;
                options.AddOption("ExportRoomsInView", "false");
                options.AddOption("VisibleElementsOfCurrentView", "false");
                // an export asks for a transaction, which is then thrown away: nothing changes in the document
                using (Transaction t = new Transaction(doc, "Meridiana IFC"))
                {
                    t.Start();
                    bool done = doc.Export(job["folder"], job["name"] + ".ifc", options);
                    t.RollBack();
                    if (!done) return "error: the export refused the model";
                }
            }
            finally
            {
                doc.Close(false);
            }
            return "ok";
        }
    }
}

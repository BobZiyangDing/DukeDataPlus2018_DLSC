import plot
import cluster
import numpy as np
import threading
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import os
import time
from data_helper import scanpy, loadTSV
from autoencoder import train, getLatentSpace

def createDir(target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

def saveTsne(filename, target_dir):
    createDir(target_dir)
    (x, y) = plot.getTsne(filename)
    l = len(x)
    with open(target_dir + "tsne.txt", "w+") as o:
        o.write(str(l) + "\n")
        for i in range(l):
            o.write(str(x[i]) + " " + str(y[i]) + "\n")

def saveKmeans(filename, target_dir, k, scvis=False):
    createDir(target_dir)
    _, k_mask = cluster.kmeans(filename, clusters=k, scvis=scvis)
    if not scvis:
        with open(target_dir + "color_mask_" + str(k) + ".txt", "w+") as o:
            for k_ in k_mask:
                o.write(str(k_) + "\n")
    else:
        with open(target_dir + "color_mask_" + str(k) + "_scvis.txt", "w+") as o:
            for k_ in k_mask:
                o.write(str(k_) + "\n")


def saveGeneList(filename, target_dir):
    createDir(target_dir)
    sc = scanpy(filename, mingenes=200, mincells=3)
    with open(target_dir + "genelist.txt", "w+") as out:
        for gene in sc.getFilteredGeneList():
            out.write(gene + "\n")

def saveGeneTable(filename, file_after_reduction, target_dir, k, scvis=False):
    createDir(target_dir)
    _, k_mask = cluster.kmeans(file_after_reduction, clusters=k, scvis=scvis)
    data = loadTSV(filename)
    indexes = []
    for _ in range(k):
        indexes.append([])
    for index in range(len(k_mask)):
        indexes[k_mask[index]].append(index)
    result = np.zeros(shape=(k, len(data[0])))
    for _ in range(k):
        result[_] = np.mean(data[indexes[_]], axis=0)
    if not scvis:
        np.savetxt(target_dir + "geneTable_" + str(k) + ".txt", result.transpose(), delimiter="\t")
    else:
        np.savetxt(target_dir + "geneTable_" + str(k) + "_scvis.txt", result.transpose(), delimiter="\t")


def savePCA(file, target_dir):
    createDir(target_dir)
    data = loadTSV(file)
    pca = PCA(n_components=10).fit_transform(data)
    print(type(pca))
    np.savetxt(target_dir + "pca.txt", pca, delimiter="\t")

def savePipeline(filtered_filename_after_reduction, filtered_filename, unfiltered_filename, target_dir):
    createDir(target_dir)
    threads = []
    start = time.time()
    # save kmeans color mask
    for k in range(1, 9):
        thread = threading.Thread(target=saveKmeans, args=(filtered_filename_after_reduction, target_dir, k))
        thread.start()
        threads.append(thread)
        print("thread {} started".format(len(threads)))
    # generate gene list
    thread = threading.Thread(target=saveGeneList, args=(unfiltered_filename, target_dir))
    threads.append(thread)
    thread.start()
    print("thread {} started".format(len(threads)))
    # save genetable
    for k in range(1, 9):
        thread = threading.Thread(target=saveGeneTable, args=(filtered_filename, filtered_filename_after_reduction,
                                                              target_dir, k))
        thread.start()
        threads.append(thread)
        print("thread {} started".format(len(threads)))
    # save tsne
    thread = threading.Thread(target=saveTsne, args=(filtered_filename_after_reduction, target_dir))
    thread.start()
    threads.append(thread)
    print("thread {} started".format(len(threads)))
    for th in threads:
        th.join()
    end = time.time()
    print("It takes {} minutes to finish the pipeline".format((end - start) / 60))


def scvisPipeline(filtered_filename_after_reduction, filtered_filename, scvis_filename, target_dir):
    createDir(target_dir)
    threads = []
    start = time.time()
    # save kmeans color mask
    for k in range(1, 9):
        thread = threading.Thread(target=saveKmeans, args=(scvis_filename, target_dir, k, True))
        thread.start()
        threads.append(thread)
        print("thread {} started".format(len(threads)))
    # save gene table
    for k in range(1, 9):
        thread = threading.Thread(target=saveGeneTable, args=(filtered_filename, filtered_filename_after_reduction,
                                                              target_dir, k, True))
        thread.start()
        threads.append(thread)
        print("thread {} started".format(len(threads)))
    # wait for all threads to end
    for th in threads:
        th.join()
    end = time.time()
    print("It takes {} minutes to finish the pipeline".format((end - start) / 60))


def realOneClick(file):
    os.chdir("./data/upload/")
    print(os.getcwd())
    filtered = scanpy(file, mincells=3, mingenes=200)
    filtered.getScanpy("./filtered.txt")

    # let a thread to train autoencoder
    t = threading.Thread(target=train, args=(file, "../../../model/upload/", 1e-2, 100, 1000))
    t.start()
    # generate none data first
    savePipeline("./filtered.txt", "./filtered.txt", file, "./none/")

    # generate pca data
    savePCA("./filtered.txt", "./pca/")
    savePipeline("./pca/pca.txt", "./filtered.txt", file, "./pca/")

    # generate autoencoder
    t.join()
    getLatentSpace("./filtered.txt", "./auto/", "../../../model/upload/")
    savePipeline("./auto/latentSpace.txt", "./filtered.txt", file, "./auto/")

    return "It's done!!!"



if __name__ == "__main__":
    #savePCA("./Website/data/Gland/filtered.txt", "./Website/data/Gland/pca/")
    scvisPipeline("./data/Gland/pca/pca.txt", "./data/Gland/filtered.txt",
                 "./data/Gland/pca/scvis.tsv", "./data/Gland/pca/")
    #data = loadTSV("./Website/data/Airway/filtered.txt")
    #print(data.shape)
    #print(np.all(np.isfinite(np.log1p(data))))
    #realOneClick("../../../data/fakedata.csv")
